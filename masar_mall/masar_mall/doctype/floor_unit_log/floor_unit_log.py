# Copyright (c) 2025, KCSC and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class FloorUnitLog(Document):

	def validate(self):
		self.check_floor_unit()

	def check_floor_unit(self):
		
		fu_doc = frappe.get_doc("Floor Unit", self.floor_unit)
		floor_units_count = frappe.db.sql("""
			SELECT COUNT(name) as count FROM `tabFloor Unit` WHERE docstatus = 1
		""")
		frappe.msgprint(str(floor_units_count))
		# for row in fu_doc:
		# 	frappe.msgprint(str(row.as_dict()))
	
