from odoo import models, fields, api, _
from odoo.exceptions import UserError


class Ubicacion (models.Model):
    _name = "conf.pmant.ubicacion"
    _description = "Ubicación de mantenimiento"

    name = fields.Char(string="Nombre", required=True)
    property_stock_inventory = fields.Many2one('stock.location', string="Ubicación de inventario", ondelete="set null", domain=[('usage', '=', 'internal')])
    property_stock_customer = fields.Many2one('stock.location', string="Ubicación de proveedor (cliente)",  ondelete="set null", domain=[('usage', '=', 'customer')])
    predeterminado = fields.Boolean(string="Predeterminado", default=True)
    operacion_entrada = fields.Many2one('stock.picking.type', string="Tipo de operación de entrada", ondelete="set null", domain=[('code', '=', 'incoming')])
    operacion_salida = fields.Many2one('stock.picking.type', string="Tipo de operación de salida", ondelete="set null", domain=[('code', '=', 'outgoing')])

    @api.constrains('predeterminado')
    def _check_only_one_default(self):
        if self.predeterminado:
            others = self.search([
                ('id', '!=', self.id),
                ('predeterminado', '=', True)
            ])
            if others:
                raise UserError(_("Solo una ubicación puede estar marcada como predeterminada."))


class CategoriasEquipos(models.Model):
    _inherit = "maintenance.equipment.category"
    _description = "Categoría de equipos"

    product_id = fields.Many2one('product.product', string="Producto relacionado", ondelete="set null",)
