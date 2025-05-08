# -*- coding: utf-8 -*-

from odoo import models, fields, api
import re # Regex modülünü import et
import logging

_logger = logging.getLogger(__name__)

class MrpProduction(models.Model):
    _inherit = "mrp.production"

    # --- Boyutlar ve İlgili Alanlar ---
    en = fields.Integer( # Integer yapıldı
        string="En (cm)",
        compute="_compute_en_boy", # Birleştirilmiş compute
        readonly=False, # Manuel düzenlemeye izin ver
        help="Ürün varyant özelliklerinden veya manuel olarak girilir (Tamsayı)."
    )
    boy = fields.Integer( # Integer yapıldı
        string="Boy (cm)",
        compute="_compute_en_boy", # Birleştirilmiş compute
        readonly=False, # Manuel düzenlemeye izin ver
        help="Ürün varyant özelliklerinden veya manuel olarak girilir (Tamsayı)."
    )
    uzunluk = fields.Integer(
        string="Uzunluk (cm)", # Etiket güncellendi
        compute="_compute_adi_aciklama_uzunluk_from_variants",
        readonly=False, # Manuel düzenlemeye izin ver
        store=False,
        help="Özel ürün varyantlarından 'uzunluk: uzunluk:' kalıbına göre çıkarılır (Tamsayı). Manuel olarak değiştirilebilir."
    )
    yogunluk = fields.Float(
        string="Yoğunluk (g/cm³)",
        default=2.5,
        readonly=False, # Manuel düzenlemeye izin ver
        store=True, # Yoğunluk genellikle sabittir, saklayalım
        help="Malzemenin yoğunluğu (varsayılan: 2.5 g/cm³)."
    )
    hacim = fields.Float(
        string="Hacim (cm³)", # Etiket güncellendi
        compute="_compute_hacim",
        # store=True, # Hesaplanan değer saklansın
        readonly=True, # Hesaplanan alan
        help="Hesaplanan hacim: En(cm) x Boy(cm) x Uzunluk(cm)",
        digits = (16, 3)  # Gösterim hassasiyeti
    )
    agirlik = fields.Float(
        string="Ağırlık (Ton)",
        compute="_compute_agirlik",
        store=True, # Hesaplanan değer saklansın
        readonly=True, # Hesaplanan alan
        help="Hesaplanan ağırlık: Hacim(cm³) x Yoğunluk(g/cm³) / 1000"
    )

    # --- Ürün Bilgileri ---
    urun_adi = fields.Char(
        string="Ürün Adı",
        compute="_compute_adi_aciklama_uzunluk_from_variants",
        store=False,
        readonly=False, # Manuel düzenlemeye izin ver
        help="Özel ürün varyantlarından 'ürün adı: ürün adı:' kalıbına göre çıkarılır. Manuel olarak değiştirilebilir."
    )
    urun_aciklama = fields.Text(
        string="Ürün Açıklama",
        compute="_compute_adi_aciklama_uzunluk_from_variants",
        store=False,
        readonly=False, # Manuel düzenlemeye izin ver
        help="Özel ürün varyantlarından 'ürün açıklama: ürün açıklama:' kalıbına göre çıkarılır. Manuel olarak değiştirilebilir."
    )

    # --- Üretim/Proje Bilgileri ---
    kalip_id = fields.Many2one(  # <<< Char'dan Many2one'a değiştirildi
        comodel_name='mrp.workcenter',  # <<< Hedef model: İş Merkezi
        string="Kalıp/İş Merkezi",
        compute="_compute_kalip",
        store=True,
        readonly=True,  # Hesaplanan alan olduğu için readonly kalabilir
        help="İlgili ilk iş emrinin iş merkezi."  # Yardım metni güncellendi
    )


    procurement_total_quant = fields.Float( # Toplam miktar küsüratlı olabilir, Float daha uygun
        string="Tedarik Grubu Toplam Miktar", # İsim güncellendi
        compute="_compute_procurement_total_quant",
        store=True, # Hesaplanan değer saklansın
        readonly=True, # Hesaplanan alan
        help="Bu üretim emrinin ait olduğu tedarik grubundaki tüm üretim emirlerinin toplam miktarı."
    )
    proje_mikari = fields.Char(
        string="Üretim İlerleme", # Etiket güncellendi
        compute="_compute_proje_miktari",
        store=True, # Hesaplanan değer saklansın
        readonly=True, # Hesaplanan alan
        help="Mevcut üretim sırası / Tedarik grubu toplam miktar"
    )

    # --- İlişkili Kayıtlar ---
    # Odoo standardında bulunan procurement_group_id alanı genellikle yeterlidir.
    # source_procurement_group_id kaldırılabilir eğer özel bir amacı yoksa.
    # sale_id ve project_id'nin compute metodları aşağıda düzeltildi.

    sale_id = fields.Many2one(
        comodel_name="sale.order",
        string="Satış Siparişi",
        compute='_compute_sale_id', # compute ile almak daha esnek
        store=True,
        readonly=True,
    )
    project_id = fields.Many2one(
        'project.project',
        string="Proje",
        compute="_compute_project_id", # Sadece bu compute kalsın
        store=True,
        # readonly=False, # Manuel değiştirilebilir olması istendi
    )

    # === COMPUTE METODLARI ===

    # En ve Boy için (Varsayılan Değer Hesaplama)
    # Not: Eğer En/Boy da product_description_variants'dan geliyorsa, bu metod yerine
    # _compute_adi_aciklama_uzunluk_from_variants metoduna eklenmelidir.
    # Bu kod, En/Boy'un ürünün variant attribute'larından geldiğini varsayar.
    @api.depends('product_id.product_template_attribute_value_ids')
    def _compute_en_boy(self):
        """
        Ürünün varyant özelliklerinden En ve Boy değerlerini alır ve Integer'a çevirir.
        Bu değerler başlangıç değeridir, manuel olarak değiştirilebilir.
        """
        for rec in self:
            # Eğer alanlar zaten manuel olarak doldurulmuşsa üzerine yazmamak iyi olabilir,
            # ama compute metodları genellikle bağımlılık değiştiğinde çalışır.
            # Şimdilik her çalıştığında hesaplayacak şekilde bırakalım.
            en_int, boy_int = 0, 0
            if rec.product_id and rec.product_id.product_template_attribute_value_ids:
                for ptav in rec.product_id.product_template_attribute_value_ids:
                    attr_name = ptav.attribute_id.name.strip().lower()
                    val_name = ptav.product_attribute_value_id.name
                    val_int = 0
                    try:
                        # Değeri sayıya çevirmeye çalış (Örn: "10 cm" -> 10)
                        numeric_val_str = ''.join(filter(str.isdigit or str == '.', val_name))
                        if numeric_val_str:
                            # Önce float'a çevirip sonra int'e çevirmek daha güvenli
                            val_int = int(float(numeric_val_str))
                    except ValueError:
                        val_int = 0
                        _logger.warning(f"Özellik ('{attr_name}':'{val_name}') tamsayıya çevrilemedi (Ürün: {rec.product_id.display_name})")

                    if attr_name == "en":
                        en_int = val_int
                    elif attr_name == "boy":
                        boy_int = val_int
            rec.en = en_int
            rec.boy = boy_int

    # Urun Adı, Açıklama ve Uzunluk için (Regex tabanlı)
    @api.depends('product_description_variants', 'product_id')
    def _compute_adi_aciklama_uzunluk_from_variants(self):
        """
        product_description_variants alanından regex kullanarak ürün adı,
        ürün açıklama ve uzunluk değerlerini çıkarır ve ilgili alanlara atar.
        Uzunluk tamsayı olarak atanır. Değerler manuel olarak değiştirilebilir.
        """
        # Regex'lerde kullanılan anahtarları kontrol edin: 'ürün adıx' mi 'ürün adı' mı?
        # Kodunuzdaki pattern'lere göre 'x' olmadan kullanıyorum:
        pattern_adi = re.compile(r"ürün adı:\s*ürün adı:\s*(.*?)\s*(?:ürün açıklama:|uzunluk:|$)", re.IGNORECASE)
        pattern_aciklama = re.compile(r"ürün açıklama:\s*ürün açıklama:\s*(.*?)\s*(?:uzunluk:|$)", re.IGNORECASE)
        pattern_uzunluk = re.compile(r"uzunluk:\s*uzunluk:\s*(\d+(?:[.,]\d+)?)\b", re.IGNORECASE)

        for rec in self:
            source_string = rec.product_description_variants
            extracted_adi = ""
            extracted_aciklama = ""
            uzunluk_int = 0

            if source_string:
                # Ürün Adı
                match_adi = pattern_adi.search(source_string)
                if match_adi: extracted_adi = match_adi.group(1).strip()
                # Ürün Açıklama
                match_aciklama = pattern_aciklama.search(source_string)
                if match_aciklama: extracted_aciklama = match_aciklama.group(1).strip()
                # Uzunluk
                match_uzunluk = pattern_uzunluk.search(source_string)
                if match_uzunluk:
                    extracted_uzunluk_str = match_uzunluk.group(1)
                    try: uzunluk_int = int(float(extracted_uzunluk_str.replace(',', '.')))
                    except ValueError: uzunluk_int = 0; _logger.warning(f"Uzunluk ('{extracted_uzunluk_str}') çevrilemedi.")

            # Fallback for urun_adi
            if not extracted_adi and rec.product_id: extracted_adi = rec.product_id.display_name

            rec.urun_adi = extracted_adi
            rec.urun_aciklama = extracted_aciklama
            rec.uzunluk = uzunluk_int

    # Hacim için
    @api.depends('en', 'boy', 'uzunluk')
    def _compute_hacim(self):
        """Hacmi cm³ cinsinden hesaplar."""
        for rec in self:
            try:
                # en, boy, uzunluk Integer
                rec.hacim = float( (rec.en or 0) * (rec.boy or 0) * (rec.uzunluk or 0) )
            except (ValueError, TypeError) as e:
                _logger.error(f"Hacim hesaplama hatası (ID: {rec.id}): {e}", exc_info=True)
                rec.hacim = 0.0

    # Ağırlık için (Hacim ve Yoğunluğa Bağlı)
    @api.depends('hacim', 'yogunluk')
    def _compute_agirlik(self):
        """ Ağırlığı Hacim (cm³) ve Yoğunluk (g/cm³) kullanarak kg cinsinden hesaplar. """
        for rec in self:
            try:
                hacim_cm3 = rec.hacim or 0.0
                dens_g_cm3 = rec.yogunluk or 0.0

                if hacim_cm3 > 0 and dens_g_cm3 > 0:
                    agirlik_gram = hacim_cm3 * dens_g_cm3
                    calculated_hacim = agirlik_gram / 1000000
                    rec.agirlik = round(calculated_hacim, 2)
                else:
                    rec.agirlik = 0.0
            except (ValueError, TypeError) as e:
                _logger.error(f"Ağırlık hesaplama hatası (ID: {rec.id}): {e}", exc_info=True)
                rec.agirlik = 0.0

    # Kalıp/İş Merkezi için (Güncellendi)
    @api.depends("workorder_ids.workcenter_id")
    def _compute_kalip(self):
        """Üretim emri ile ilişkili ilk iş emrinin iş merkezini (kayıt olarak) atar."""
        for rec in self:
            # İlk uygun iş emrinin iş merkezini bul
            # Eğer workorder_ids boşsa veya ilk iş emrinin workcenter'ı yoksa False ata
            if rec.workorder_ids and rec.workorder_ids[0].workcenter_id:
                # .name yerine doğrudan workcenter ID'sini (kaydı) ata
                rec.kalip_id = rec.workorder_ids[0].workcenter_id
            else:
                # Many2one alanı için boş değer False veya None'dur
                rec.kalip_id = False

    # Tedarik Grubu Toplam Miktarı için
    @api.depends("procurement_group_id.mrp_production_ids.product_qty")
    def _compute_procurement_total_quant(self):
        """İlişkili tedarik grubundaki tüm üretim emirlerinin toplam miktarını hesaplar."""
        for rec in self:
            if rec.procurement_group_id:
                mrp_productions = self.env['mrp.production'].search([
                    ('procurement_group_id', '=', rec.procurement_group_id.id)
                ])
                rec.procurement_total_quant = sum(mrp_productions.mapped("product_qty"))
            else:
                # Eğer grup yoksa, sadece kendi üretim miktarını gösterelim
                rec.procurement_total_quant = rec.product_qty

    # Üretim İlerleme Göstergesi için
    @api.depends('backorder_sequence', 'procurement_total_quant') # Bağımlılık doğru
    def _compute_proje_miktari(self):
        """Üretim ilerlemesini "Mevcut Sıra / Toplam Miktar" formatında gösterir."""
        for rec in self:
            # Miktarı .0 olmadan gösterelim
            total_quant_str = str(int(rec.procurement_total_quant or 0))
            # backorder_sequence 0'dan başlar, 1 ekleyerek göstermek daha anlaşılır olabilir
            # Kullanıcı beklentisine göre karar verin. Şimdilik 0'dan başlatıyorum.
            rec.proje_mikari = f"{rec.backorder_sequence} / {total_quant_str}"

    # Satış Siparişi için (Compute ile)
    @api.depends('procurement_group_id.sale_id')
    def _compute_sale_id(self):
        """Procurement Group üzerinden Sale Order'ı bulur."""
        for rec in self:
            # Odoo standardında mrp.production'da procurement_group_id zaten var.
            rec.sale_id = rec.procurement_group_id.sale_id if rec.procurement_group_id else False

    # Proje için (Compute ile)
    @api.depends('sale_id.project_ids') # sale_id compute ile geldiği için ona bağlamak daha iyi
    def _compute_project_id(self):
        """Satış siparişi ile ilişkili ilk projeyi bulur."""
        for rec in self:
            if rec.sale_id and rec.sale_id.project_ids:
                # Birden fazla proje varsa ilkini alır. Mantık değişebilir.
                rec.project_id = rec.sale_id.project_ids[0]
            else:
                rec.project_id = False




# # -*- coding: utf-8 -*-
#
# from odoo import models, fields, api
# import re # Regex modülünü import et
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class MrpProduction(models.Model):
#     _inherit = "mrp.production"
#
#     en = fields.Char(string="En (cm)", compute="_compute_en", readonly=False,)
#     boy = fields.Char(string="Boy (cm)", compute="_compute_boy", readonly=False,)
#
#     hacim = fields.Float(string="Hacim (kg)", compute="_compute_hacim", readonly=False,)
#
#     kalip_id = fields.Char(string="Kalip",  compute="_compute_kalip")
#
#     procurement_total_quant = fields.Integer(string="Toplam Talep", compute="_compute_production_progress")
#     proje_mikari = fields.Char(string="Proje Miktarı", compute = "_compute_proje_miktari")
#
#     source_procurement_group_id = fields.Many2one(
#         comodel_name="procurement.group",
#         readonly=True,
#     )
#     sale_id = fields.Many2one(
#         comodel_name="sale.order",
#         string="Sale order",
#         readonly=True,
#         store=True,
#         related="source_procurement_group_id.sale_id",
#     )
#
#     project_id = fields.Many2one(
#         'project.project',
#         string="Proje",
#         compute="_compute_project_id",
#         store=True,
#         readonly=False,  # Gerekirse editable yapabilirsin
#     )
#
#     # --- Yoğunluk Alanı (Yeni) ---
#     yogunluk = fields.Float(
#         string="Yoğunluk (g/cm³)",
#         default=2.5,  # Varsayılan değer 2.5
#         readonly=False,  # Manuel olarak değiştirilebilir
#         store=True,  # Veritabanında saklansın
#         help="Malzemenin yoğunluğu (varsayılan: 2.5 g/cm³)."
#     )
#
#     agirlik = fields.Float(
#         string="Ağırlık (kg)",
#         compute="_compute_agirlik",  # Yeni veya güncellenmiş compute metodu
#         store=True,  # Hesaplanan değer saklansın
#         readonly=True,  # Hesaplanan alan, genellikle değiştirilmez
#         help="Hesaplanan ağırlık: En(cm) x Boy(cm) x Uzunluk(cm) x Yoğunluk(g/cm³) / 1000"
#     )
#
#     # === Ağırlık İçin COMPUTE METODU ===
#     @api.depends('en', 'boy', 'uzunluk', 'yogunluk')
#     def _compute_agirlik(self):
#         """
#         Ağırlığı En, Boy, Uzunluk (cm) ve Yoğunluk (g/cm³) kullanarak kg
#         cinsinden hesaplar.
#         """
#         for rec in self:
#             try:
#                 # Boyutları ve yoğunluğu alalım (None ise 0 kabul edelim)
#                 # En/Boy Float, Uzunluk Integer, Yoğunluk Float varsayılıyor
#                 en_cm = rec.en or 0.0
#                 boy_cm = rec.boy or 0.0
#                 # Uzunluk Integer olduğu için hesaplamada float'a çevirelim
#                 uzunluk_cm = float(rec.uzunluk or 0)
#                 dens_g_cm3 = rec.yogunluk or 0.0
#
#                 # Hesaplama sadece tüm değerler pozitifse anlamlıdır
#                 if en_cm > 0 and boy_cm > 0 and uzunluk_cm > 0 and dens_g_cm3 > 0:
#                     hacim_cm3 = en_cm * boy_cm * uzunluk_cm
#                     agirlik_gram = hacim_cm3 * dens_g_cm3
#                     agirlik_kg = agirlik_gram / 1000.0
#                     rec.agirlik = agirlik_kg
#                 else:
#                     # Geçersiz veya eksik veri durumunda ağırlık 0 olur
#                     rec.agirlik = 0.0
#
#             except (ValueError, TypeError) as e:
#                 # Hesaplama sırasında bir hata olursa loglayıp 0 atayalım
#                 _logger.error(f"Ağırlık hesaplama hatası (Kayıt ID: {rec.id}): {e}", exc_info=True)
#                 rec.agirlik = 0.0
#
#     @api.depends('source_procurement_group_id.sale_id.project_ids')
#     def _compute_project_id(self):
#         for rec in self:
#             sale_order = rec.source_procurement_group_id.sale_id
#             if sale_order and sale_order.project_ids:
#                 rec.project_id = sale_order.project_ids[0]
#             else:
#                 rec.project_id = False
#
#     def _compute_en(self):
#         for rec in self:
#             en_attribs = rec.product_variant_attributes.filtered(lambda attr: attr.attribute_id.name == "En")
#             print(rec.product_id.product_template_variant_value_ids)
#             print("asa")
#             rec.en = en_attribs.product_attribute_value_id.name
#
#     def _compute_boy(self):
#         for rec in self:
#             en_attribs = rec.product_variant_attributes.filtered(lambda attr: attr.attribute_id.name == "Boy")
#             rec.boy = en_attribs.product_attribute_value_id.name
#
#
#
#
#     # --- İlgili Alan Tanımları (store=False, readonly=False) ---
#     urun_adi = fields.Char(
#         string="Ürün Adı",
#         compute="_compute_adi_aciklama_uzunluk_from_variants",
#         # store=True, # KALDIRILDI
#         readonly=False,  # EKLENDİ
#         help="Otomatik hesaplanır, ancak manuel olarak değiştirilebilir."
#     )
#     urun_aciklama = fields.Text(  # veya fields.Char
#         string="Ürün Açıklama",
#         compute="_compute_adi_aciklama_uzunluk_from_variants",
#         # store=True, # KALDIRILDI
#         readonly=False,  # EKLENDİ
#         help="Otomatik hesaplanır, ancak manuel olarak değiştirilebilir."
#     )
#     uzunluk = fields.Integer(
#         string="Uzunluk",
#         compute="_compute_adi_aciklama_uzunluk_from_variants",
#         # store=True, # KALDIRILDI
#         readonly=False,  # EKLENDİ
#         help="Otomatik hesaplanır (Tamsayı), ancak manuel olarak değiştirilebilir."
#     )
#
#     # === İlgili COMPUTE METODU ===
#     # Bu metodun içeriği öncekiyle aynı kalır, çünkü hesaplama mantığı değişmedi.
#     # Sadece alan tanımları değişti.
#     @api.depends('product_description_variants', 'product_id')
#     def _compute_adi_aciklama_uzunluk_from_variants(self):
#         """
#         product_description_variants alanından regex kullanarak ürün adı,
#         ürün açıklama ve uzunluk değerlerini çıkarır ve ilgili alanlara atar.
#         Uzunluk tamsayı olarak atanır. Alanlar readonly=False olduğu için
#         bu metodun hesapladığı değerler başlangıç değeri gibidir, üzerine yazılabilir.
#         """
#         # Regex Kalıpları (Büyük/küçük harf duyarsız)
#         pattern_adi = re.compile(r"ürün adı:\s*ürün adı:\s*(.*?)\s*(?:ürün açıklama:|uzunluk:|$)", re.IGNORECASE)
#         pattern_aciklama = re.compile(r"ürün açıklama:\s*ürün açıklama:\s*(.*?)\s*(?:uzunluk:|$)", re.IGNORECASE)
#         pattern_uzunluk = re.compile(r"uzunluk:\s*uzunluk:\s*(\d+(?:[.,]\d+)?)\b", re.IGNORECASE)
#
#         for rec in self:
#             # Kaynak string'i al
#             source_string = rec.product_description_variants
#             extracted_adi = ""
#             extracted_aciklama = ""
#             uzunluk_int = 0  # Integer için varsayılan değer
#
#             if source_string:
#                 # 1. Ürün Adı
#                 match_adi = pattern_adi.search(source_string)
#                 if match_adi:
#                     extracted_adi = match_adi.group(1).strip()
#
#                 # 2. Ürün Açıklama
#                 match_aciklama = pattern_aciklama.search(source_string)
#                 if match_aciklama:
#                     extracted_aciklama = match_aciklama.group(1).strip()
#
#                 # 3. Uzunluk
#                 match_uzunluk = pattern_uzunluk.search(source_string)
#                 if match_uzunluk:
#                     extracted_uzunluk_str = match_uzunluk.group(1)
#                     try:
#                         # Önce float'a çevir, sonra integer'a çevir
#                         uzunluk_int = int(float(extracted_uzunluk_str.replace(',', '.')))
#                     except ValueError:
#                         _logger.warning(
#                             f"Uzunluk değeri ('{extracted_uzunluk_str}') sayıya/tamsayıya çevrilemedi. Kaynak: '{source_string}', Kayıt ID: {rec.id}")
#                         uzunluk_int = 0
#
#             # Fallback for urun_adi
#             if not extracted_adi and rec.product_id:
#                 extracted_adi = rec.product_id.display_name
#
#             # Hesaplanan değerleri ilgili alanlara ata
#             # Not: Eğer kullanıcı bu alanları manuel olarak değiştirdiyse ve
#             # 'product_description_variants' değişmediyse, bu atamalar
#             # bir sonraki form açılışında/kaydedilişinde tekrar yapılabilir.
#             # Kalıcı manuel değişiklik için inverse fonksiyon gerekebilir.
#             rec.urun_adi = extracted_adi
#             rec.urun_aciklama = extracted_aciklama
#             rec.uzunluk = uzunluk_int
#
#
#
#     # @api.depends("en", "boy", "uzunluk")
#     # def _compute_agirlik(self):
#     #     for rec in self:
#     #         rec.agirlik = int(rec.en) + int(rec.boy) + 10
#
#     @api.depends("procurement_group_id.mrp_production_ids.product_qty")
#     def _compute_production_progress(self):
#         for rec in self:
#             mrp_productions = rec.procurement_group_id.mrp_production_ids
#             if not mrp_productions:
#                 rec.remaining_quantity = 0
#                 continue
#
#
#             # Toplam üretilen miktarı hesapla
#             total_produced = sum(mrp_productions.mapped("product_qty"))
#
#             # İlk üretimden kalan miktarı hesapla
#             rec.procurement_total_quant = total_produced
#
#     @api.depends("sale_id")
#     def _compute_proje(self):
#         for rec in self:
#             rec.project_id = "asa"
#
#             hast = [rec.sale_id.project_ids]
#             rec.project_id =hast[0].name
#             print(hast)
#             # total_quantity = sum(rec.procurement_group_id.mrp_production_ids.mapped("product_qty"))
#             # rec.project_id = total_quantity
#
#     @api.depends("sale_id")
#     def _compute_kalip(self):
#         for rec in self:
#             rec.kalip_id = "asa"
#             oplar = [rec.workorder_ids][0]
#             rec.kalip_id = oplar.workcenter_id.name
#
#
#
#
#     def _compute_proje_miktari(self):
#         for rec in self:
#             rec.proje_mikari = str(rec.backorder_sequence) + " / " +  str(rec.procurement_total_quant)