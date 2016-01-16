def rowcol_from_template(target_tab, template_tab=0):
	"""Adjusts row heights and column widths to match the template

	Parameters
	----------
	target_tab: Integer
	\tTable to be adjusted
	template_tab: Integer, defaults to 0
	\tTemplate table

	"""

	for row, tab in list(S.row_heights.keys()):
		# Delete all row heights in target table
		if tab == target_tab:
			S.row_heights.pop((row, tab))

		if tab == template_tab:
			S.row_heights[(row, target_tab)] = \
				S.row_heights[(row, tab)]

	for col, tab in list(S.col_widths.keys()):
		# Delete all column widths in target table
		if tab == target_tab:
			S.col_widths.pop((col, tab))

		if tab == template_tab:
			S.col_widths[(col, target_tab)] = \
					S.col_widths[(col, tab)]

	return "Table {tab} adjusted.".format(tab=target_tab)

def cell_attributes_from_template(target_tab, template_tab=0):
	"""Adjusts cell paarmeters to match the template

	Parameters
	----------
	target_tab: Integer
	\tTable to be adjusted
	template_tab: Integer, defaults to 0
	\tTemplate table

	"""

	new_cell_attributes = []
	for attr in S.cell_attributes:
		if attr[1] == template_tab:
			new_attr = (attr[0], target_tab, attr[2])
			new_cell_attributes.append(new_attr)
	S.cell_attributes.extend(new_cell_attributes)

	return "Table {tab} adjusted.".format(tab=target_tab)

# Shortcuts

rc = rowcol_from_template
ca = cell_attributes_from_template