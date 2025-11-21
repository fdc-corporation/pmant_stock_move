from odoo import models, fields, api, _
from odoo.exceptions import UserError



class TareaPamnt (models.Model):
    _inherit = "tarea.mantenimiento"
    _description = "Tarea de mantenimiento"


    # grupo_id = fields.Many2one('procurement.group', string="Grupo de entregas", ondelete="set null",)
    len_movimientos = fields.Integer(string="Número de entregas", compute="_compute_len_movimientos", store=False)
    state_recepcion = fields.Selection( [("recepcionado", "Recepcionado"),("confirm_recepcion", "Sin recepcion"),("entregado", "Devuelto al cliente"), ("cancelado", "Cancelado"), ("borrador", "Borrador") ], default="confirm_recepcion", string="Estados de recepción")
    is_confirm_recepcion = fields.Boolean(string="Confirmar recepción", default=False, help="Indica si la recepción de los equipos ha sido confirmada.")
    requerimientos_ids = fields.One2many("stock.move", "tarea_id", string="Requerimientos de stock")


    def create(self, vals):
        res = super(TareaPamnt, self).create(vals)
        if "state_recepcion" in vals:
            res.state_recepcion = 'confirm_recepcion'
        return res

    def cancel_confirm (self):
        for record in self:
            if record.state_recepcion != "cancelado":
                record.state_recepcion = "cancelado"
                movimientos = self.env["stock.picking"].search([("tarea_id", "=", record.id)])
                for movimiento in movimientos:
                    if movimiento.state != "done":
                        for equipo in record.planequipo:
                            if equipo.equipo.serial_no:
                                serie = self.env["stock.lot"].search([("name", "=", equipo.equipo.serial_no)], limit=1)
                                if serie:
                                    serie.unlink()
                        movimiento.action_cancel()
                    

    def restart_confirm (self):
        for record in self:
            if record.state_recepcion != "borrador":
                record.state_recepcion = "borrador"
                record.is_confirm_recepcion = False

    def action_confirm_recepcion(self):
        for record in self:
            # grupo = False
            # if not record.grupo_id :
            #     grupo = self.env["procurement.group"].create({
            #         "name": f"{record.name}",
            #         "move_type": "direct",
            #         "partner_id": record.ubicacion.id if record.ubicacion else record.cliente.id,
            #     })
            # else :
            #     grupo = record.grupo_id
            # record.grupo_id = grupo.id
            ubicaciones = self.env["conf.pmant.ubicacion"].search([
                ('id', '!=', self.id),
                ('predeterminado', '=', True)
            ])
            movimientos = self.env["stock.picking"].create({
                # UBICACION DEL PROVEEDOR
                "location_id": ubicaciones.property_stock_customer.id if ubicaciones else self.env.ref('stock.stock_location_customers').id,
                # UBICACION DE INVENTARIO
                "location_dest_id": ubicaciones.property_stock_inventory.id if ubicaciones else self.env.ref('stock.stock_location_stock').id,
                # TIPO DE OPERACIÓN
                "picking_type_id": ubicaciones.operacion_entrada.id if ubicaciones else self.env.ref('stock.picking_type_in').id,
                "origin": record.name,
                # "group_id": grupo.id,
                "partner_id": record.ubicacion.id if record.ubicacion else record.cliente.id,
                "state": "assigned",
                "tarea_id": record.id,})
            n_series = []
            for equipo in record.planequipo:
                if not equipo.equipo.category_id.product_id:
                    raise UserError(_("El equipo %s no tiene un producto relacionado en su categoría.") % (equipo.name))
                if not equipo.equipo.serial_no:
                    raise UserError(_("El equipo %s no tiene un número de serie asignado.") % (equipo.name))
                serie = self.env["stock.lot"].search([("name", "=", equipo.equipo.serial_no)], limit=1)
                if not serie :
                    serie = self.env["stock.lot"].create({
                        "name": equipo.equipo.serial_no,
                        "product_id": equipo.equipo.category_id.product_id.id,
                        "company_id": self.env.company.id,
                    })
                else : 
                    serie = serie[0]
                n_series.append(serie.id)
                self.env["stock.move"].create({
                        "product_id": equipo.equipo.category_id.product_id.id,
                        "description_picking" : f"{equipo.equipo.name} { '- Modelo:' + equipo.equipo.model if equipo.equipo.model else ''  }",
                        "product_uom_qty": 1,
                        "lot_ids" : [(6, 0, n_series)],
                        "picking_type_id": movimientos.picking_type_id.id,
                        "location_id": movimientos.location_id.id,
                        "location_dest_id": movimientos.location_dest_id.id,
                        "picking_id": movimientos.id,
                        # "group_id": grupo.id,
                })
                record.state_recepcion = "confirm_recepcion"
            record.is_confirm_recepcion = True

    def action_view_entregas(self):
        self.ensure_one()
        # if not self.grupo_id:
        #     raise UserError(_("No hay grupo de entregas asociado a esta tarea."))

        entregas = self.env["stock.picking"].search([("tarea_id", "=", self.id)])
        if not entregas:
            raise UserError(_("No hay entregas asociadas a este grupo."))

        return {
            "name": "Recepcion de equipos",
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "view_mode": "list,form",
            "domain": [("id", "in", entregas.ids)],
        }


    def _compute_len_movimientos(self):
        for record in self:
            if record.id:
                movimientos = self.env["stock.picking"].search([("tarea_id", "=", record.id)])
                record.len_movimientos = len(movimientos)
            else:
                record.len_movimientos = 0


class Movimientos(models.Model):
    _inherit = "stock.picking"
    _description = "Entrega de stock"

    tarea_id = fields.Many2one('tarea.mantenimiento', string="Tarea de mantenimiento", ondelete="set null",)
    len_tarea = fields.Integer(string="Número de tareas", compute="_compute_len_tarea", store=False)

    def _compute_len_tarea(self):
        for record in self:
            record.len_tarea = len(record.tarea_id)

    def action_view_tarea(self):
        self.ensure_one()

        return {
            "name": "Tarea de mantenimiento",
            "type": "ir.actions.act_window",
            "res_model": "tarea.mantenimiento",
            "view_mode": "form",
            "res_id": self.tarea_id.id,
        }

    def button_validate(self):
        res = super(Movimientos, self).button_validate()
        for record in self:
            if record.picking_type_id.code == "incoming" and record.tarea_id:
                record.tarea_id.state_recepcion = "recepcionado"
            elif record.picking_type_id.code == "outgoing" and record.tarea_id:
                record.tarea_id.state_recepcion = "entregado"
        return res

