from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"
    _description = "Sale Order"

    is_confirm_repuestos = fields.Boolean(string="Repuestos confirmados", compute="_compute_is_confirm_repuestos", default=False)
    is_confirm_devolucion = fields.Boolean(string="Devolución confirmada", compute="_compute_is_confirm_repuestos", default=False)
    is_confirm_desecho = fields.Boolean(string="Desecho confirmado", compute="_compute_is_confirm_repuestos", default=False)
    len_mov_repuestos = fields.Integer(string="Número de repuestos", compute="_compute_len_mov_repuestos", default=False)
    len_mov_devolucion = fields.Integer(string="Número de devoluciones", compute="_compute_len_mov_devolucion", default=False)
    len_mov_desecho = fields.Integer(string="Número de desechos", compute="_compute_len_mov_desecho", default=False)
    
    def _compute_is_confirm_repuestos(self):
        for record in self:
            if record.ots:
                record.is_confirm_repuestos = record.ots.is_confirm_repuestos
                record.is_confirm_devolucion = record.ots.vissible_devolucion
                record.is_confirm_desecho = record.ots.vissible_desecho

    def _compute_len_mov_repuestos(self):
        for record in self:
            if record.id:
                requerimientos = self.env["stock.picking"].search(
                    [("tarea_id", "=", record.ots.id), ("is_requerimiento", "=", True)]
                )
                record.len_mov_repuestos = len(requerimientos)
            else:
                record.len_mov_repuestos = 0

    def _compute_len_mov_devolucion(self):
        for record in self:
            if record.id:
                requerimientos = self.env["stock.picking"].search(
                    [("tarea_id", "=", record.ots.id), ("is_devolucion_repuesto", "=", True)]
                )
                record.len_mov_devolucion = len(requerimientos)
            else:
                record.len_mov_devolucion = 0

    def _compute_len_mov_desecho(self):
        for record in self:
            if record.id:
                requerimientos = self.env["stock.scrap"].sudo().search(
                    [("tarea_id", "=", record.id)]
                )
                record.len_mov_desecho = len(requerimientos)
            else:
                record.len_mov_desecho = 0
                
    def action_view_mov_repuestos(self):
        self.ensure_one()
        return {
            "name": "Movimientos de repuestos",
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "view_mode": "tree,form",
            "domain": [("tarea_id", "=", self.ots.id), ("is_requerimiento", "=", True)],
        }
        
    def action_view_repuestos (self):
        self.ensure_one()

        requerimientos = self.env["stock.picking"].search(
            [("tarea_id", "=", self.ots.id), ("is_requerimiento", "=", True)]
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

    def action_view_desecho_repuestos(self):
        self.ensure_one()

        desechos = self.env["stock.scrap"].search(
            [("tarea_id", "=", self.ots.id)]
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


    def action_view_devoluciones(self):
        self.ensure_one()

        devoluciones = self.env["stock.picking"].search(
            [("tarea_id", "=", self.ots.id), ("is_devolucion_repuesto", "=", True)]
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
