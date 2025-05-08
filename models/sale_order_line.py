# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class SaleOrderLine(models.Model):
    """
    Inherits sale.order.line to link Manufacturing Orders by filtering
    the parent Sale Order's existing mrp_production_ids field based on the line's product.
    Satırın ürününe göre ana Satış Siparişinin mevcut mrp_production_ids alanını
    filtreleyerek Üretim Emirlerini bağlamak için sale.order.line'ı devralır.
    """
    _inherit = 'sale.order.line'

    mrp_production_count = fields.Integer(
        "Related MO Count (Filtered from SO)", # Alan etiketi güncellendi
        compute='_compute_mrp_from_order', # Hesaplama metodu yeniden adlandırıldı
        store=False, # Performans için saklanmaz
        help="Number of Manufacturing Orders from the parent Sale Order "
             "that match the product on this line.", # Yardım metni güncellendi
        groups='mrp.group_mrp_user') # MRP kullanıcıları için görünürlük
    mrp_production_ids = fields.Many2many(
        'mrp.production',
        string='Related MOs (Filtered from SO)', # Alan etiketi güncellendi
        compute='_compute_mrp_from_order', # Hesaplama metodu yeniden adlandırıldı
        store=False, # Performans için saklanmaz
        help="Manufacturing Orders from the parent Sale Order "
             "that match the product on this line.", # Yardım metni güncellendi
        copy=False, # Kopyalamayı engelle
        groups='mrp.group_mrp_user') # MRP kullanıcıları için görünürlük

    # Bağımlılık order_id'nin mrp_production_ids alanına ve satırın product_id'sine olmalı
    @api.depends('order_id.mrp_production_ids', 'product_id')
    def _compute_mrp_from_order(self):
        """
        Computes Manufacturing Orders (MOs) for the Sale Order Line by
        filtering the MOs already computed on the parent Sale Order.
        It takes the `mrp_production_ids` from the `sale.order` and
        filters them to include only those matching the product_id of this line.

        Ana Satış Siparişinde zaten hesaplanmış olan ÜE'leri filtreleyerek
        Satış Siparişi Satırı için Üretim Emirlerini (ÜE) hesaplar.
        `sale.order`'dan `mrp_production_ids`'yi alır ve bunları yalnızca
        bu satırın `product_id`'si ile eşleşenleri içerecek şekilde filtreler.
        """
        # Başlangıçta tüm satırlar için alanları sıfırla/boşalt
        # self.mrp_production_ids = False # Many2many için False atamak yerine boş kayıt kümesi atamak daha iyi
        # self.mrp_production_count = 0

        for line in self:
            # Satırın bağlı olduğu siparişteki tüm ÜE'leri al
            # Eğer order_id boşsa veya mrp_production_ids hesaplanmamışsa (None olabilir) kontrol et
            order_mos = line.order_id.mrp_production_ids if line.order_id else self.env['mrp.production']

            # Bu ÜE'leri satırın ürününe göre filtrele
            # Eğer product_id boşsa veya order_mos boşsa, filtreleme boş sonuç döndürecektir
            product_specific_mos = order_mos.filtered(lambda mo: mo.product_id == line.product_id)

            # Sonuçları ata
            line.mrp_production_ids = product_specific_mos
            line.mrp_production_count = len(product_specific_mos)

    def action_view_mrp_production(self):
        """
        Action to open the view for Manufacturing Orders related to the sale order line,
        filtered by the product on the line (using the computation based on SO's MOs).
        Satırdaki ürüne göre filtrelenmiş (SO'nun ÜE'lerine dayalı hesaplamayı kullanarak)
        satış siparişi satırıyla ilgili Üretim Emirleri görünümünü açma eylemi.
        """
        self.ensure_one()
        # Hesaplanan alanı kullanarak üretim ID'lerini al
        mrp_production_ids = self.mrp_production_ids

        action = {
            'res_model': 'mrp.production',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', mrp_production_ids.ids)],
            'context': {'default_origin': self.order_id.name, 'default_product_id': self.product_id.id}
        }

        if len(mrp_production_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': mrp_production_ids.id,
                'views': [(False, 'form')],
            })
        else:
            action.update({
                'name': _("MOs for %s (Product: %s)", self.order_id.name, self.product_id.display_name),
                'view_mode': 'tree,form',
                'views': [(False, 'tree'), (False, 'form')],
            })
        return action
