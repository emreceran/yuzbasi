# -*- coding: utf-8 -*-
# from odoo import http


# class Yuzbasi(http.Controller):
#     @http.route('/yuzbasi/yuzbasi', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/yuzbasi/yuzbasi/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('yuzbasi.listing', {
#             'root': '/yuzbasi/yuzbasi',
#             'objects': http.request.env['yuzbasi.yuzbasi'].search([]),
#         })

#     @http.route('/yuzbasi/yuzbasi/objects/<model("yuzbasi.yuzbasi"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('yuzbasi.object', {
#             'object': obj
#         })

