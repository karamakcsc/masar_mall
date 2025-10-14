# Copyright (c) 2025, KCSC and contributors
# For license information, please see license.txt

import frappe
from dateutil.relativedelta import relativedelta
from frappe.utils import add_months, get_last_day, getdate, flt
from frappe.model.document import Document
from masar_mall.utils.create_log import create_log, create_floor_unit_log


class LeaseContract(Document):
    def on_submit(self):
        frappe.set_value(self.doctype, self.name, "status", "Rent")
        self.create_lease_schedule()
        self.update_floor_unit()
        if self.renewed_from:
            self.renew_lease(self.renewed_from)
        create_log(self)

    def validate(self):
        self.validate_dates()
        self.check_allowance_options()
        self.calculate_period_in_months()
        self.check_pay_type_against_period()
        self.validate_renewal_link()

    def validate_dates(self):
        if self.lease_start and self.lease_end:
            if self.lease_start > self.lease_end:
                frappe.throw("Lease start date cannot be after lease end date.")
        elif not self.lease_start or not self.lease_end:
            frappe.throw("Both lease start and lease end dates must be provided.")

    def check_allowance_options(self):
        """Ensure only one of in_period or out_period is selected"""
        if getattr(self, "in_period", False) and getattr(self, "out_period", False):
            frappe.throw("You cannot select both 'Inside the Billing Period' and 'Outside the Billing Period'. Please choose only one option.")

    def calculate_period_in_months(self):
        if hasattr(self, 'lease_start') and hasattr(self, 'lease_end') and self.lease_start and self.lease_end:
            start_date = frappe.utils.getdate(self.lease_start)
            end_date = frappe.utils.getdate(self.lease_end)
            delta = relativedelta(end_date, start_date)
            lease_months = delta.years * 12 + delta.months + (1 if delta.days > 0 else 0)

            allowance_months = int(getattr(self, 'allowance_period', 0) or 0)

            if getattr(self, 'in_period', False):
                self.period_in_months = lease_months
            elif getattr(self, 'out_period', False):
                self.period_in_months = lease_months + allowance_months
            else:
                self.period_in_months = lease_months

    def check_pay_type_against_period(self):
        """Validate that selected pay_type fits within lease period"""
        pay_type_map = {
            "1 month": 1,
            "2 month": 2,
            "3 month": 3,
            "6 month": 6,
            "1 year": 12
        }

        interval = pay_type_map.get(self.billing_frequency, 1)
        period = getattr(self, 'period_in_months', 0)

        if interval > period:
            frappe.throw(
                f"Payment type '{self.billing_frequency}' is longer than the lease period of {period} month(s). Please choose a smaller payment type."
            )

    def create_lease_schedule(self):
        if not self.rent_details:
            frappe.throw("Rent details are required to create lease schedule")
        
        schedule = frappe.new_doc("Lease Contract Schedule")
        schedule.lease_contract = self.name
        
        start_date = getdate(self.lease_start)
        end_date = getdate(self.lease_end)
        allowance_months = int(getattr(self, 'allowance_period', 0) or 0)

        pay_type_map = {
            "1 month": 1,
            "2 month": 2,
            "3 month": 3,
            "6 month": 6,
            "1 year": 12
        }
        billing_frequency = getattr(self, 'billing_frequency', '') or ''
        billing_interval = pay_type_map.get(billing_frequency, 1)
        total_rent = flt(getattr(self, 'total_rent_amount', 0))
        total_months = int(getattr(self, 'period_in_months', 0))
        
        tax_status = self.get_tax_status()
        
        monthly_rent = total_rent / total_months if total_months > 0 else 0
        
        if getattr(self, 'in_period', False):
            self.add_free_months(schedule, start_date, allowance_months)
            paid_start = add_months(start_date, allowance_months)
            paid_months = total_months - allowance_months
            paid_end = end_date
        elif getattr(self, 'out_period', False):
            paid_start = start_date
            paid_months = total_months
            paid_end = end_date
        else:
            paid_start = start_date
            paid_months = total_months
            paid_end = end_date
        
        self.add_paid_invoices(schedule, paid_start, paid_end, paid_months, billing_interval, monthly_rent, tax_status)
        
        if getattr(self, 'out_period', False) and allowance_months > 0:
            free_start = add_months(end_date, 1)
            self.add_free_months(schedule, free_start, allowance_months)
        
        schedule.total_peroid = total_months
        schedule.save(ignore_permissions=True)
        schedule.submit()
        self.status = "Rent"
        frappe.db.commit()
        frappe.msgprint("Lease Contract Schedule has been created successfully.", alert=True, indicator="green")

    def get_tax_status(self):
        if not getattr(self, "include_vat", False):
            return "Exempt"
        
        if not getattr(self, "tax_template", None):
            return "Exempt"
        
        try:
            tax_doc = frappe.get_doc("Sales Taxes and Charges Template", self.tax_template)
            return "Taxable" if getattr(tax_doc, "taxes", None) else "Exempt"
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Failed to get tax template")
            return "Exempt"

    def add_free_months(self, schedule, start_date, num_months):
        current_date = start_date
        
        for i in range(num_months):
            period_start = current_date
            period_end = get_last_day(period_start)
            
            schedule.append("invoice", {
                "lease_start": period_start,
                "lease_end": period_end,
                "amount": 0,
                "rate": 0,
                "tax": "Exempt",
                "is_allowance": 1
            })
            
            current_date = add_months(current_date, 1)

    def add_paid_invoices(self, schedule, start_date, end_date, total_months, billing_interval, monthly_rent, tax_status):
        if total_months <= 0:
            return
        
        current_date = start_date
        remaining_months = total_months
        
        while remaining_months > 0:
            months_in_invoice = min(billing_interval, remaining_months)
            period_start = current_date
            
            if remaining_months <= billing_interval:
                period_end = end_date
            else:
                period_end = get_last_day(add_months(period_start, months_in_invoice - 1))
            
            invoice_amount = monthly_rent * months_in_invoice
            
            schedule.append("invoice", {
                "lease_start": period_start,
                "lease_end": period_end,
                "amount": invoice_amount,
                "rate": 0,
                "tax": tax_status,
                "is_allowance": 0
            })
            
            current_date = add_months(current_date, months_in_invoice)
            remaining_months -= months_in_invoice

    def validate_renewal_link(self):
        """Validate that renewed_from field links to a valid contract"""
        if self.renewed_from:
            if not frappe.db.exists("Lease Contract", self.renewed_from):
                frappe.throw(f"The contract '{self.renewed_from}' does not exist.")
            
            original_status = frappe.db.get_value("Lease Contract", self.renewed_from, "status")
            if original_status != "Renewal":
                frappe.msgprint(
                    f"Warning: The original contract '{self.renewed_from}' status is '{original_status}', not 'Renewal'.",
                    alert=True,
                    indicator="orange"
                )

    def update_floor_unit(self):
        if self.rent_details:
            for floor in self.rent_details:
                if floor.floor_unit:
                    frappe.db.set_value("Floor Unit", floor.floor_unit, "rent_space", 1)
                    frappe.db.set_value("Floor Unit", floor.floor_unit, "tenant", self.tenant_lessee)
                    try:
                        floor_unit_doc = frappe.get_doc("Floor Unit", floor.floor_unit)
                        create_floor_unit_log(floor_unit_doc)
                    except Exception as e:
                        frappe.throw(f"Error Logging Floor Unit: {e}")
            frappe.db.commit()

    # def update_rent_schedule_html(self):
    #     """Generate HTML table showing monthly and total accumulated rent."""
    #     if not self.lease_start or not self.lease_end or not self.total_rent_amount:
    #         return "<p style='color:red;'>Missing lease start, end date, or total rent amount.</p>"

    #     start_date = getdate(self.lease_start)
    #     end_date = getdate(self.lease_end)

    #     delta = relativedelta(end_date, start_date)
    #     total_months = delta.years * 12 + delta.months + (1 if delta.days > 0 else 0)
    #     if total_months <= 0:
    #         return "<p style='color:red;'>Invalid lease period.</p>"

    #     monthly_rent = flt(self.total_rent_amount) / total_months
    #     total_accumulated = 0

    #     html = """
    #     <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width:100%;">
    #         <tr style="background-color:#f2f2f2; text-align:center;">
    #             <th>Month #</th>
    #             <th>Month Start</th>
    #             <th>Month End</th>
    #             <th>Monthly Rent</th>
    #             <th>Total Accumulated</th>
    #         </tr>
    #     """

    #     current_date = start_date
    #     for i in range(1, total_months + 1):
    #         month_start = current_date
    #         month_end = get_last_day(month_start)
    #         total_accumulated += monthly_rent

    #         html += f"""
    #         <tr style="text-align:center;">
    #             <td>{i}</td>
    #             <td>{month_start.strftime('%Y-%m-%d')}</td>
    #             <td>{month_end.strftime('%Y-%m-%d')}</td>
    #             <td>{monthly_rent:,.2f}</td>
    #             <td>{total_accumulated:,.2f}</td>
    #         </tr>
    #         """

    #         current_date = add_months(current_date, 1)

    #     html += "</table>"
    #     return html

    @frappe.whitelist()        
    def terminate_lease(self):
        if self.rent_details:
            for floor in self.rent_details:
                if floor.floor_unit:
                    try:
                        floor_unit_doc = frappe.get_doc("Floor Unit", floor.floor_unit)
                        floor_unit_doc.release_from_lease()
                    except Exception as e:
                        frappe.throw(f"Error Reverse Unit SE: {e}")
            
            frappe.db.set_value(self.doctype, self.name, "status", "Terminated")
            frappe.db.commit()
            
            self.reload()
            create_log(self)
            
            frappe.msgprint("Lease contract terminated successfully.", alert=True, indicator="orange")
    
    @frappe.whitelist()
    def renew_lease(self, renewal_self):
        renewal_doc = frappe.get_doc("Lease Contract", renewal_self)
        frappe.db.set_value(renewal_doc.doctype, renewal_doc.name, "status", "Renewal")
        frappe.db.commit()
        renewal_doc.reload()
        create_log(renewal_doc)
        
        frappe.msgprint("Contract marked for renewal.", alert=True, indicator="blue")

    @frappe.whitelist()
    def legal_case(self):
        frappe.db.set_value(self.doctype, self.name, "status", "Legal Case")
        frappe.db.commit()
