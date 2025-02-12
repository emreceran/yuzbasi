# -*- coding: utf-8 -*-

from odoo import models, fields

class MrpProduction(models.Model):
    _inherit = "mrp.production"

    en = fields.Float(string="En (cm)")
    boy = fields.Float(string="Boy (cm)")
    uzunluk = fields.Float(string="Uzunluk (m)")
    agirlik = fields.Float(string="Ağırlık (kg)")
    urun_adi = fields.Char(string="Ürün Adı")
    urun_aciklama = fields.Char(string="Ürün Açıklama")
    kalip_id = fields.Many2one('mrp.workcenter', string="Kalip")
    project_id = fields.Many2one('project.project', string="Proje")
