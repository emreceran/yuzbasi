# -*- coding: utf-8 -*-

from odoo import models, fields, api

class MrpProduction(models.Model):
    _inherit = "mrp.production"

    en = fields.Char(string="En (cm)", compute="_compute_en")
    boy = fields.Char(string="Boy (cm)", compute="_compute_boy")
    uzunluk = fields.Char(string="Uzunluk (m)", compute="_compute_uzunluk")
    agirlik = fields.Float(string="Ağırlık (kg)")
    urun_adi = fields.Char(string="Ürün Adı", compute="_compute_urun_adi")
    urun_aciklama = fields.Char(string="Ürün Açıklama")
    kalip_id = fields.Many2one('mrp.workcenter', string="Kalip")
    project_id = fields.Char(string="Proje", compute="_compute_proje")
    procurement_total_quant = fields.Integer(string="Toplam Talep", compute="_compute_production_progress")
    proje_mikari = fields.Char(string="Proje Miktarı", compute = "_compute_proje_miktari")

    def _compute_en(self):
        for rec in self:
            en_attribs = rec.product_variant_attributes.filtered(lambda attr: attr.attribute_id.name == "En")
            rec.en = en_attribs.product_attribute_value_id.name

    def _compute_boy(self):
        for rec in self:
            en_attribs = rec.product_variant_attributes.filtered(lambda attr: attr.attribute_id.name == "Yükseklik")
            rec.boy = en_attribs.product_attribute_value_id.name

    def _compute_uzunluk(self):
        for rec in self:
            en_attribs = rec.product_variant_attributes.filtered(lambda attr: attr.attribute_id.name == "Uzunluk")
            rec.uzunluk = en_attribs.product_attribute_value_id.name



    @api.depends("product_id.name")
    def _compute_urun_adi(self):
        for rec in self:
            rec.urun_adi = rec.product_id.name

    @api.depends("procurement_group_id.mrp_production_ids.product_qty")
    def _compute_production_progress(self):
        for rec in self:
            mrp_productions = rec.procurement_group_id.mrp_production_ids
            if not mrp_productions:
                rec.remaining_quantity = 0
                continue


            # Toplam üretilen miktarı hesapla
            total_produced = sum(mrp_productions.mapped("product_qty"))

            # İlk üretimden kalan miktarı hesapla
            rec.procurement_total_quant = total_produced

    @api.depends("procurement_group_id.mrp_production_ids.product_qty")
    def _compute_proje(self):
        for rec in self:
            total_quantity = sum(rec.procurement_group_id.mrp_production_ids.mapped("product_qty"))

            rec.project_id = total_quantity

    def _compute_proje_miktari(self):
        for rec in self:
            rec.proje_mikari = str(rec.backorder_sequence) + " / " +  str(rec.procurement_total_quant)