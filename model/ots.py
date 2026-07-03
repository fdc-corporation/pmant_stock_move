from odoo import models, fields, api, _ 
from odoo.exceptions import UserError


class MaintenanceRequest(models.Model):
    _inherit = "maintenance.request"

    def crm_oportunidad_create(self):
        for rec in self:
            equipos = rec.tarea.planequipo.mapped("equipo.id") if rec.tarea else []
            valores = {
                "name": rec.name,
                "user_id": (
                    rec.employee_id.user_id.id
                    if rec.employee_id and rec.employee_id.user_id
                    else False
                ),
                "partner_id": rec.empresa.id if rec.empresa else False,
                "ubicacion": rec.ubicacion.id if rec.ubicacion else False,
                "orden_trabajo": rec.id,
                "equipo_tarea": [(6, 0, equipos)],
                "repuestos_ids": [(6, 0, rec.tarea.requerimientos_ids.ids)] if rec.tarea else []
            }
            lead = self.env["crm.lead"].create(valores)
            rec.oportunidad = lead.id
            return {
                "type": "ir.actions.act_window",
                "name" : "Oportunidad",
                "view_mode" : "form",
                "res_model" : "crm.lead",
                "res_id" : lead.id,
                "context" : {"create" : False}
            }




class CRMLead(models.Model):
    _inherit = "crm.lead"

    repuestos_ids = fields.Many2many("requerimientos.stock", string="Repuestos requeridos")

    def btn_cotizacion (self):
        res = super().btn_cotizacion()
        cotizacion_id = res['res_id']

        for record in self:
            for repuesto in record.repuestos_ids:
                self.env['sale.order.line'].create({
                    'order_id' : cotizacion_id,
                    'ots' : self.orden_trabajo.id,
                    'product_id' : repuesto.product_id.id,
                    'product_uom_qty' : repuesto.cantidad,
                })
            return {
                "type": "ir.actions.act_window",
                "name": "Cotización",
                "view_mode": "form",
                "res_model": "sale.order",
                "res_id": cotizacion_id,
                "context": {"create": False},
            }
