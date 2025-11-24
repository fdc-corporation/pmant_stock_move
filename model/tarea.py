from odoo import models, fields, api, _
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class TareaPamnt(models.Model):
    _inherit = "tarea.mantenimiento"
    _description = "Tarea de mantenimiento"

    # grupo_id = fields.Many2one('procurement.group', string="Grupo de entregas", ondelete="set null",)
    len_movimientos = fields.Integer(
        string="Número de entregas", compute="_compute_len_movimientos", store=False
    )
    state_recepcion = fields.Selection(
        [
            ("recepcionado", "Recepcionado"),
            ("confirm_recepcion", "Sin recepcion"),
            ("entregado", "Devuelto al cliente"),
            ("cancelado", "Cancelado"),
            ("borrador", "Borrador"),
        ],
        default="confirm_recepcion",
        string="Estados de recepción",
    )
    is_confirm_recepcion = fields.Boolean(
        string="Confirmar recepción",
        default=False,
        help="Indica si la recepción de los equipos ha sido confirmada.",
    )
    requerimientos_ids = fields.One2many(
        "requerimientos.stock", "tarea_id", string="Requerimientos de stock"
    )
    is_solicitado = fields.Boolean(string="Repuestos solicitados")
    len_req_repuestos = fields.Integer(
        string="Número de requerimientos", compute="_compute_len_repuestos", store=False
    )
    is_confirm_repuestos = fields.Boolean(
        string="Repuestos confirmados",
        default=False,
        help="Indica si los repuestos han sido confirmados.",
    )
    confirm_desecho = fields.Boolean(string="Confirmar desecho de equipo", default=False)
    confirm_devolucion = fields.Boolean(string="Confirmar devolución de equipo", default=False)
    len_mov_desechos = fields.Integer(
        string="Número de desechos", compute="_compute_desechos")
    vissible_desecho = fields.Boolean(string="Visible desecho de equipo", default=False)
    vissible_devolucion = fields.Boolean(string="Visible devolución de equipo", default=False)  
    len_mov_devoluciones = fields.Integer(
        string="Número de devoluciones", compute="_compute_len_devolucion")
    

    def _compute_len_devolucion(self):
        for record in self:
            if record.id:
                requerimientos = self.env["stock.picking"].search(
                    [("tarea_id", "=", record.id), ("is_devolucion_repuesto", "=", True)]
                )
                record.len_mov_devoluciones = len(requerimientos)
            else:
                record.len_mov_devoluciones = 0

    def _compute_desechos(self):
        for record in self:
            if record.id:
                requerimientos = self.env["stock.scrap"].sudo().search(
                    [("tarea_id", "=", record.id)]
                )
                record.len_mov_desechos = len(requerimientos)
            else:
                record.len_mov_desechos = 0
    def create(self, vals):
        res = super(TareaPamnt, self).create(vals)
        if "state_recepcion" in vals:
            res.state_recepcion = "confirm_recepcion"
        return res



    def _compute_len_repuestos(self):
        for record in self:
            if record.id:
                requerimientos = self.env["stock.picking"].search(
                    [("tarea_id", "=", record.id), ("is_requerimiento", "=", True)]
                )
                record.len_req_repuestos = len(requerimientos)
            else:
                record.len_req_repuestos = 0

    def cancel_confirm(self):
        for record in self:
            if record.state_recepcion != "cancelado":
                record.state_recepcion = "cancelado"
                movimientos = self.env["stock.picking"].search(
                    [("tarea_id", "=", record.id)]
                )
                for movimiento in movimientos:
                    if movimiento.state != "done":
                        for equipo in record.planequipo:
                            if equipo.equipo.serial_no:
                                serie = self.env["stock.lot"].search(
                                    [("name", "=", equipo.equipo.serial_no)], limit=1
                                )
                                if serie:
                                    serie.unlink()
                        movimiento.action_cancel()

    def restart_confirm(self):
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
            ubicaciones = self.env["conf.pmant.ubicacion"].search(
                [("id", "!=", self.id), ("predeterminado", "=", True)]
            )
            movimientos = self.env["stock.picking"].create(
                {
                    # UBICACION DEL PROVEEDOR
                    "location_id": (
                        ubicaciones.property_stock_customer.id
                        if ubicaciones
                        else self.env.ref("stock.stock_location_customers").id
                    ),
                    # UBICACION DE INVENTARIO
                    "location_dest_id": (
                        ubicaciones.property_stock_inventory.id
                        if ubicaciones
                        else self.env.ref("stock.stock_location_stock").id
                    ),
                    # TIPO DE OPERACIÓN
                    "picking_type_id": (
                        ubicaciones.operacion_entrada.id
                        if ubicaciones
                        else self.env.ref("stock.picking_type_in").id
                    ),
                    "origin": record.name,
                    # "group_id": grupo.id,
                    "partner_id": (
                        record.ubicacion.id if record.ubicacion else record.cliente.id
                    ),
                    "state": "assigned",
                    "tarea_id": record.id,
                }
            )
            n_series = []
            for equipo in record.planequipo:
                if not equipo.equipo.category_id.product_id:
                    raise UserError(
                        _(
                            "El equipo %s no tiene un producto relacionado en su categoría."
                        )
                        % (equipo.name)
                    )
                if not equipo.equipo.serial_no:
                    raise UserError(
                        _("El equipo %s no tiene un número de serie asignado.")
                        % (equipo.name)
                    )
                serie = self.env["stock.lot"].search(
                    [("name", "=", equipo.equipo.serial_no)], limit=1
                )
                if not serie:
                    serie = self.env["stock.lot"].create(
                        {
                            "name": equipo.equipo.serial_no,
                            "product_id": equipo.equipo.category_id.product_id.id,
                            "company_id": self.env.company.id,
                        }
                    )
                else:
                    serie = serie[0]
                n_series.append(serie.id)
                self.env["stock.move"].create(
                    {
                        "product_id": equipo.equipo.category_id.product_id.id,
                        "description_picking": f"{equipo.equipo.name} { '- Modelo:' + equipo.equipo.model if equipo.equipo.model else ''  }",
                        "product_uom_qty": 1,
                        "lot_ids": [(6, 0, n_series)],
                        "picking_type_id": movimientos.picking_type_id.id,
                        "location_id": movimientos.location_id.id,
                        "location_dest_id": movimientos.location_dest_id.id,
                        "picking_id": movimientos.id,
                        # "group_id": grupo.id,
                    }
                )
                record.state_recepcion = "confirm_recepcion"
            record.is_confirm_recepcion = True

    def action_view_entregas(self):
        self.ensure_one()
        # if not self.grupo_id:
        #     raise UserError(_("No hay grupo de entregas asociado a esta tarea."))

        entregas = self.env["stock.picking"].search(
            [("tarea_id", "=", self.id), ("is_requerimiento", "=", False)]
        )
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
                movimientos = self.env["stock.picking"].search(
                    [("tarea_id", "=", record.id), ("is_requerimiento", "=", False)]
                )
                record.len_movimientos = len(movimientos)
            else:
                record.len_movimientos = 0

    def action_solicitar_repuestos(self):
        for record in self:
            mensaje = f"🛠 Solicitud de repuestos para la tarea: {record.name}\n\n"
            mensaje += "🔧 Repuestos requeridos:\n"
            for req in record.requerimientos_ids:
                mensaje += (
                    f"- {req.product_id.display_name} (Cantidad: {req.cantidad})\n"
                )

            # Buscar usuario con grupo planificador o administrador
            grupo = self.env.ref(
                "pmant.group_pmant_planner", raise_if_not_found=False
            ) or self.env.ref("pmant.group_pmant_admin", raise_if_not_found=False)
            user = False
            if grupo:
                user = (
                    self.env["res.users"]
                    .sudo()
                    .search(
                        [("group_ids", "in", grupo.id), ("share", "=", False)], limit=1
                    )
                )

            # Verificar si existe partner vinculado
            partner = user.partner_id if user and user.partner_id else False

            # Solo enviar mensaje si hay partner válido
            if partner:
                record.message_post(
                    body=mensaje,
                    partner_ids=[partner.id],
                    message_type="notification",
                    subtype_xmlid="mail.mt_note",
                )
            else:
                _logger.warning(
                    "⚠️ No se encontró partner válido para enviar la notificación."
                )
                raise UserError(
                    _(
                        "No se encontró un usuario planner válido para enviar la notificación."
                    )
                )
            record.is_solicitado = True

    def action_create_mov(self):
        for record in self:
            conf = self.env["conf.pmant.ubicacion"].search(
                [("is_trasporte_interno", "=", True)], limit=1
            )
            if not conf:
                raise UserError(
                    _("No hay una ubicación configurada para traslados internos.")
                )
            movimientos = self.env["stock.picking"].create(
                {
                    "partner_id": self.env.company.partner_id.id,
                    # UBICACION ORIGEN TRASLADO INTERNO
                    "location_id": conf.ubicacion_origen_traslado.id,
                    # UBICACION DESTINO TRASLADO INTERNO
                    "location_dest_id": conf.ubicacion_destino_traslado.id,
                    # TIPO DE OPERACIÓN TRASLADO INTERNO
                    "picking_type_id": conf.tipo_operacion_traslado.id,
                    "origin": record.name,
                    "state": "assigned",
                    "tarea_id": record.id,
                    "is_requerimiento": True,
                }
            )
            for req in record.requerimientos_ids:
                self.env["stock.move"].create(
                    {
                        "product_id": req.product_id.id,
                        "description_picking": req.nota or req.product_id.display_name,
                        "product_uom_qty": req.cantidad,
                        "picking_type_id": movimientos.picking_type_id.id,
                        "location_id": movimientos.location_id.id,
                        "location_dest_id": movimientos.location_dest_id.id,
                        "picking_id": movimientos.id,
                    }
                )
            record.is_confirm_repuestos = True
            return {
                "name": "Requerimientos de repuestos",
                "type": "ir.actions.act_window",
                "res_model": "stock.picking",
                "view_mode": "list,form",
                "domain": [("id", "=", movimientos.id)],
            }
    def action_view_repuestos (self):
        self.ensure_one()

        requerimientos = self.env["stock.picking"].search(
            [("tarea_id", "=", self.id), ("is_requerimiento", "=", True)]
        )
        if not requerimientos:
            raise UserError(_("No hay requerimientos de repuestos asociados a esta tarea."))

        return {
            "name": "Requerimientos de repuestos",
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "view_mode": "list,form",
            "domain": [("id", "in", requerimientos.ids)],
        }


    def action_consumir_repuestos(self):
        for record in self:
            record.confirm_desecho = False
            record.vissible_desecho = True
            # Buscar configuración de ubicación de desecho
            conf = self.env["conf.pmant.ubicacion"].search(
                [("is_ubicacion_desecho", "=", True)],
                limit=1
            )

            if not conf:
                raise UserError("No se ha configurado una ubicación de desecho.")

            for req in record.requerimientos_ids:
                if req.cant_consumido > 0:
                    self.env["stock.scrap"].create({
                        "product_id": req.product_id.id,
                        "scrap_qty": req.cant_consumido,
                        "location_id": conf.ubicacion_desecho.id,  # Corregido aquí
                        "scrap_location_id": conf.scrap_location_id.id,
                        "tarea_id": record.id,
                        "scrap_reason_tag_ids": [(6, 0, conf.motivo_desecho.ids)],
                    })
            
            
    def action_view_desecho_repuestos(self):
        self.ensure_one()

        desechos = self.env["stock.scrap"].search(
            [("tarea_id", "=", self.id)]
        )
        if not desechos:
            raise UserError(_("No hay desechos de repuestos asociados a esta tarea."))

        return {
            "name": "Desechos de repuestos",
            "type": "ir.actions.act_window",
            "res_model": "stock.scrap",
            "view_mode": "list,form",
            "domain": [("id", "in", desechos.ids)],
        }

    def action_devolucion_repuesto(self):
        for record in self:
            record.confirm_devolucion = False
            conf = self.env["conf.pmant.ubicacion"].search(
                [("is_trasporte_interno", "=", True)], limit=1
            )
            if not conf:
                raise UserError(
                    _("No hay una ubicación configurada para devoluciones de repuestos.")
                )
            movimientos = self.env["stock.picking"].create(
                {
                    "partner_id": self.env.company.partner_id.id,
                    # UBICACION DESTINO TRASLADO INTERNO
                    "location_dest_id": conf.ubicacion_origen_traslado.id,
                    # UBICACION ORIGEN TRASLADO INTERNO
                    "location_id": conf.ubicacion_destino_traslado.id,
                    # TIPO DE OPERACIÓN TRASLADO INTERNO
                    "picking_type_id": conf.tipo_operacion_traslado.id,
                    "origin": record.name,
                    "state": "assigned",
                    "tarea_id": record.id,
                    "is_devolucion_repuesto": True,
                }
            )
            for req in record.requerimientos_ids:
                if req.cantidad > 0:
                    self.env["stock.move"].create(
                        {
                            "product_id": req.product_id.id,
                            "description_picking": req.nota or req.product_id.display_name,
                            "product_uom_qty": req.cantidad,
                            "picking_type_id": movimientos.picking_type_id.id,
                            "location_id": movimientos.location_id.id,
                            "location_dest_id": movimientos.location_dest_id.id,
                            "picking_id": movimientos.id,
                        }
                    )
            record.vissible_devolucion = True
            return {
                "name": "Devolución de repuestos",
                "type": "ir.actions.act_window",
                "res_model": "stock.picking",
                "view_mode": "list,form",
                "domain": [("id", "=", movimientos.id)],
            }

    def action_view_devoluciones(self):
        self.ensure_one()

        devoluciones = self.env["stock.picking"].search(
            [("tarea_id", "=", self.id), ("is_devolucion_repuesto", "=", True)]
        )
        if not devoluciones:
            raise UserError(_("No hay devoluciones de repuestos asociadas a esta tarea."))

        return {
            "name": "Devoluciones de repuestos",
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "view_mode": "list,form",
            "domain": [("id", "in", devoluciones.ids)],
        }
class Movimientos(models.Model):
    _inherit = "stock.picking"
    _description = "Entrega de stock"

    tarea_id = fields.Many2one(
        "tarea.mantenimiento",
        string="Tarea de mantenimiento",
        ondelete="set null",
    )
    len_tarea = fields.Integer(
        string="Número de tareas", compute="_compute_len_tarea", store=False
    )
    is_requerimiento = fields.Boolean(
        string="¿Es un requerimiento de repuesto?", default=False
    )
    is_devolucion_repuesto = fields.Boolean(
        string="¿Es una devolución de repuesto?", default=False
    )

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


class DesechosStock(models.Model):
    _inherit = "stock.scrap"
    _description = "Desecho de stock"

    tarea_id = fields.Many2one(
        "tarea.mantenimiento",
        string="Tarea de mantenimiento",
        ondelete="set null",
    )