# -*- coding: utf-8 -*-
# ©  2011,2013 Michael Telahun Makonnen <mmakonnen@gmail.com>
# ©  2014 initOS GmbH & Co. KG <http://www.initos.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import fields, models, api, _
from openerp.exceptions import Warning as UserError


class HrPublicHolidaysLine(models.Model):
    _name = 'hr.holidays.public.line'
    _description = 'Public Holidays Lines'
    _order = "date, name desc"

    name = fields.Char(
        'Name',
        required=True,
    )
    date = fields.Date(
        'Date',
        required=True
    )
    year_id = fields.Many2one(
        'hr.holidays.public',
        'Calendar Year',
        required=True,
    )
    variable = fields.Boolean('Date may change')
    c_city_ids = fields.Many2many('ouc.city', 'ouc_hr_holidays_public_rel', 'c_ph_id', 'c_city_id', 'Related City')
    state_ids = fields.Many2many('res.country.state', 'ouc_phl_state_rel', 'phl_id', 'state_id', 'Related State')
    # state_ids = fields.Many2many(
    #     'res.country.state',
    #     'hr_holiday_public_state_rel',
    #     'line_id',
    #     'state_id',
    #     'Related States'
    # )


    @api.multi
    @api.constrains('date', 'c_city_ids')
    def _check_date_state(self):
        for r in self:
            r._check_date_state_one()

    def _check_date_state_one(self):
        if fields.Date.from_string(self.date).year != self.year_id.year:
            raise UserError(_(
                'Dates of holidays should be the same year '
                'as the calendar year they are being assigned to'
            ))
        if self.c_city_ids:
            domain = [('date', '=', self.date),
                      ('year_id', '=', self.year_id.id),
                      ('c_city_ids', '!=', False),
                      ('id', '!=', self.id)]
            holidays = self.search(domain)
            for holiday in holidays:
                if self.c_city_ids & holiday.c_city_ids:
                    raise UserError(_('You can\'t create duplicate public '
                                      'holiday per date %s and one of the '
                                      'country states.') % self.date)
        domain = [('date', '=', self.date),
                  ('year_id', '=', self.year_id.id),
                  ('c_city_ids', '=', False)]
        if self.search_count(domain) > 1:
            raise UserError(_('You can\'t create duplicate public holiday '
                            'per date %s.') % self.date)
        return True

class ouc_city(models.Model):
    _name = 'ouc.city'

    name = fields.Char(string='City Name', required=True)
    state_id = fields.Many2one('res.country.state', string='State', required=True)
    country_id = fields.Many2one('res.country', string='Country', required=True)
    active = fields.Boolean(string='Active', default=True)