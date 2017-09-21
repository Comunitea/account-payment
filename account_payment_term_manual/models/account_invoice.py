# -*- coding: utf-8 -*-
# © 2017 Comunitea Servicios Tecnológicos S.L.
#        (http://comunitea.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp
from datetime import timedelta



class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    manual_term = fields.Boolean("Manual Payment Term ")

    @api.multi
    def compute(self, value, date_ref=False):
        self.ensure_one
        result = []
        if not self.env.context.get('manual_term'):
            result = super(AccountPaymentTerm, self).compute(value,
                                                            date_ref)
        else:
            result.append([])
            date_ref = date_ref or fields.Date.today()
            amount = value
            if self.env.context.get('currency_id'):
                currency = self.env['res.currency'].browse(
                    self.env.context['currency_id'])
            else:
                currency = self.env.user.company_id.currency_id
            prec = currency.decimal_places
            ipt = self._context.get('initial_payment_type')
            ipa= self._context.get('initial_payment_amount')
            nop = self._context.get('number_of_payments')
            if nop <= 0 :
                raise UserError(_('Wrong number of payments. Please correct '
                                  'it in Invoice') )
            if ipt == 'fixed':
                first_amt = round(ipa, prec)
                result[0].append((date_ref, first_amt))
            else:
                first_amt = round(value * (ipa / 100.0), prec)
                result[0].append((date_ref, first_amt))
            res_amt = amount - first_amt
            if res_amt:
                date_ref = fields.Date.to_string(fields.Date.from_string(
                    date_ref) + timedelta(
                    days=30))
                if nop < 2:
                    raise UserError(
                        _('Wrong number of payments. Please correct '
                          'it in Invoice'))
                line_amt = round(res_amt / (nop-1), prec)
                for x in range(1, nop-1):

                    result[0].append((date_ref, line_amt))
                    res_amt -= line_amt
                    date_ref = fields.Date.to_string(fields.Date.from_string(
                        date_ref) + timedelta(
                        days=30))
            if res_amt:
                result[0].append((date_ref, res_amt))
        return result





class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    manual_term_check = fields.Boolean(related='payment_term_id.manual_term')
    initial_payment_type = fields.Selection([
            ('percent', 'Percent'),
            ('fixed', 'Fixed Amount')],
        string='Initial Payment Type', required=False, default='percent',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="Select here the kind of valuation related to first payment term "
             "line.")
    initial_payment_amount = fields.Float(
        string='Initial payment (fixed or %)', required=False,
        readonly=True, states={'draft': [('readonly', False)]})
    number_of_payments = fields.Integer(default=2, readonly=True,
        states={'draft': [('readonly', False)]},
        help="Number of payments included initial.")

    @api.multi
    def action_move_create(self):
        for inv in self:
            if inv.manual_term_check:
                super(AccountInvoice, self.with_context(
                    manual_term=True,
                    initial_payment_type=inv.initial_payment_type,
                    initial_payment_amount=inv.initial_payment_amount,
                    number_of_payments=inv.number_of_payments
                )).action_move_create()
            else:
                super(AccountInvoice, self).action_move_create()

    @api.multi
    def action_view_payments(self):
        action = self.env.ref(
            'account_payment_term_manual.action_invoice_payments_short').read(

        )[0]
        action['domain'] = [('stored_invoice_id', 'in', [self.id]),
                            ('account_id.internal_type', 'in',
                             ['receivable', 'payable'])]
        return action
