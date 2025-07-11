import PyPDF2
from datetime import datetime
import pandas as pd
import re

pdf_file = PyPDF2.PdfReader("test_data/Customer Invoice Details6.PDF")
# Define DataFrame with proper column types
df = pd.DataFrame({
    "report_entity": pd.Series(dtype='object'),
    "transaction_date": pd.Series(dtype='object'),
    "invoice_id": pd.Series(dtype='object'),
    "dun_id": pd.Series(dtype='object'),
    "invoice_to": pd.Series(dtype='object'),
    "sold_to": pd.Series(dtype='object'),
    "ship_to": pd.Series(dtype='object'),
    "currency": pd.Series(dtype='object'),
    "customer_id": pd.Series(dtype='object'),
    "store_id": pd.Series(dtype='object'),
    "sales_order_id": pd.Series(dtype='object'),
    "customer_po": pd.Series(dtype='object'),
    "terms_str": pd.Series(dtype='object'),
    "ship_via": pd.Series(dtype='object'),
    "department_id": pd.Series(dtype='object'),
    "cartons_count": pd.Series(dtype='int64'),
    "cartons_net_weight": pd.Series(dtype='float64'),
    "cartons_net_weight_unit": pd.Series(dtype='object'),
    "cartons_gross_weight": pd.Series(dtype='float64'),
    "cartons_gross_weight_unit": pd.Series(dtype='object'),
    "style_color": pd.Series(dtype='object'),
    "style_color_descr": pd.Series(dtype='object'),
    "size": pd.Series(dtype='object'),
    "qty": pd.Series(dtype='int64'),
    "product_family": pd.Series(dtype='object'),
    "country_of_origin": pd.Series(dtype='object'),
    "rds_certified": pd.Series(dtype='int64'),
    "tariff_code": pd.Series(dtype='object'),
    "delivery_id": pd.Series(dtype='object'),
    "other_descr": pd.Series(dtype='object'),
    "price": pd.Series(dtype='float64'),
    "ext_price": pd.Series(dtype='float64')
})

df_summary  = pd.DataFrame({
    "report_entity": pd.Series(dtype='object'),
    "transaction_date": pd.Series(dtype='object'),
    "invoice_id": pd.Series(dtype='object'),
    "dun_id": pd.Series(dtype='object'),
    "invoice_to": pd.Series(dtype='object'),
    "sold_to": pd.Series(dtype='object'),
    "ship_to": pd.Series(dtype='object'),
    "total_units": pd.Series(dtype='int64'),
    "merchandise_total": pd.Series(dtype='float64'),
    "merchandise_total_unit": pd.Series(dtype='object'),
    "freight_total": pd.Series(dtype='float64'),
    "freight_total_unit": pd.Series(dtype='object'),
    "total_invoice": pd.Series(dtype='float64'),
    "total_invoice_unit": pd.Series(dtype='object')
})

pages = []
init_page_values = {
    "report_entity": '',
    "transaction_date": '',
    "invoice_id": '',
    "dun_id": '',

    'invoice_to': '',
    'sold_to': '',
    'ship_to': '',
    'currency': '',
    'customer_id': '',
    'store_id': '',
    'sales_order_id': '',
    'customer_po': '',
    'terms_str': '',
    'ship_via': '',
    'department_id': '',
    'cartons_count': 0,
    'cartons_net_weight': 0.0,
    'cartons_net_weight_unit': '',
    'cartons_gross_weight': 0.0,
    'cartons_gross_weight_unit': '',

    'total_units': 0,
    'merchandise_total': 0.0,
    'merchandise_total_unit': '',
    'freight_total': 0.0,
    'freight_total_unit': '',
    'total_invoice': 0.0,
    'total_invoice_unit': ''
}

for page in pdf_file.pages:
    """
    1. use REMIT PAYMENT TO to identify the last page
    2. Currency\n can only appear on the 1st page
    """
    init_page_sep = 'Currency\n'
    other_page_sep = '\n'
    last_page_sep = 'REMIT PAYMENT  TO\n \n'
    # split the page content into 3 blocks
    # 1st block is by string Invoice #\n
    # 1st page would have a block 3
    block1 = page.extract_text().split(" Invoice #\n")[0]
    block1_other = block1.split(' Date')
    # dun #
    dun_match = re.search(r'DUN#(\d{9})', block1)
    dun_id = dun_match.group(1) if dun_match else None
    # just scrape the report entity, no complex logic needed
    report_entity = ''.join(block1_other[0][:-10].split('\n')[1:])
    block_remain = page.extract_text().split(" Invoice #\n")[1]

    # Extract invoice_id and validate it's a 9-digit integer
    invoice_match = re.search(r'(\d{9})', block1_other[1])
    invoice_id = invoice_match.group(1) if invoice_match else None

    # Extract and validate date string in mm/dd/yyyy format
    date_match = re.search(r'(\d{2}/\d{2}/\d{4})', block1_other[0])
    if date_match:
        try:
            transaction_date = datetime.strptime(date_match.group(1), '%m/%d/%Y').strftime('%Y-%m-%d')
        except ValueError:
            transaction_date = '9999-12-31'
    else:
        transaction_date = None

    init_page_values.update({
        'report_entity': report_entity,
        'transaction_date': transaction_date,
        'invoice_id': invoice_id,
        'dun_id': dun_id,
    })

    # first page has a extra black, treat it as a separate page
    if init_page_sep in block_remain:
        block2 = block_remain.split(init_page_sep)[0]
        block3 = block_remain.split(init_page_sep)[1]
        block3_other = block3.split(other_page_sep)
        # invoice_to, sold_to, ship_to
        # easy parsing
        invoice_to = ''.join(block2.split('\n')[1:4]).strip().replace('SOLD TO:', '')
        sold_to = ''.join(block2.split('\n')[4:7]).strip().replace('SHIP TO:', '')
        ship_to = ''.join(block2.split('\n')[7:10]).strip()
        # currency - validate it's exactly 3 characters
        currency_match = re.search(r'([A-Z]{3})', block2.split('\n')[-1])
        currency = currency_match.group(1) if currency_match else None
        # customer_id - validate it's an 8-digit number
        customer_match = re.search(r'(\d{8})', block3_other[0])
        customer_id = customer_match.group(1) if customer_match else None

        store_id = '' # placeholder for now

        # sales_order_id - validate it's a 9-digit number
        sales_order_match = re.search(r'(\d{9})', block3_other[2])
        sales_order_id = sales_order_match.group(1) if sales_order_match else None

        customer_po = block3_other[3].split('Customer PO')[0].strip().split('No. of Cartons')[-1].strip()
        terms_str = block3_other[0].split('Terms')[0].strip()
        ship_via = '' # placeholder for now
        department_id = '' # placeholder for now
        cartons_count = int(block3_other[3].split('Customer PO')[0].strip().split('No. of Cartons')[0].strip())

        # Validate net weight - must be 3 decimal number
        net_weight_match = re.search(r'(\d+\.\d{3})', block3_other[4].split('Net Weight :')[-1].strip())
        cartons_net_weight = net_weight_match.group(1) if net_weight_match else None
        if cartons_net_weight:
            # Validate net weight unit - must be 2 uppercase letters
            net_unit_match = re.search(r'([A-Z]{2})', block3_other[4].split('Net Weight :')[-1].strip())
            cartons_net_weight_unit = net_unit_match.group(1) if net_unit_match else None
        else:
            cartons_net_weight_unit = None

        # Validate gross weight - must be 3 decimal number
        gross_weight_match = re.search(r'(\d+\.\d{3})', block3_other[5].split('Gross Weight :')[0].strip())
        cartons_gross_weight = gross_weight_match.group(1) if gross_weight_match else None
        
        if cartons_gross_weight:
            # Validate gross weight unit - must be 2 uppercase letters
            gross_unit_match = re.search(r'([A-Z]{2})', block3_other[5].split('Gross Weight :')[0].strip())
            cartons_gross_weight_unit = gross_unit_match.group(1) if gross_unit_match else None
        else:
            cartons_gross_weight_unit = None

        # save down initial page to static dict
        init_page_values.update({
            'invoice_to': str(invoice_to) if invoice_to is not None else '',
            'sold_to': str(sold_to) if sold_to is not None else '',
            'ship_to': str(ship_to) if ship_to is not None else '',
            'currency': str(currency) if currency is not None else '',
            'customer_id': str(customer_id) if customer_id is not None else '',
            'store_id': str(store_id) if store_id is not None else '',
            'sales_order_id': str(sales_order_id) if sales_order_id is not None else '',
            'customer_po': str(customer_po) if customer_po is not None else '',
            'terms_str': str(terms_str) if terms_str is not None else '',
            'ship_via': str(ship_via) if ship_via is not None else '',
            'department_id': str(department_id) if department_id is not None else '',
            'cartons_count': int(cartons_count) if cartons_count is not None else 0,
            'cartons_net_weight': float(cartons_net_weight) if cartons_net_weight is not None else 0.0,
            'cartons_net_weight_unit': str(cartons_net_weight_unit) if cartons_net_weight_unit is not None else '',
            'cartons_gross_weight': float(cartons_gross_weight) if cartons_gross_weight is not None else 0.0,
            'cartons_gross_weight_unit': str(cartons_gross_weight_unit) if cartons_gross_weight_unit is not None else ''
        })
    # treat last page
    elif last_page_sep in page.extract_text():
        summary_info = block_remain.split('\n NO RETURNS ACCEPTED WITHOUT AUTHORIZATION.')[0].split('Total Units ')[1].split('\n')
        total_units = summary_info[0]
        merchandise_total = float(summary_info[1].split('Merchandise Total')[1].strip().split(' ')[0])
        merchandise_total_unit = summary_info[1].split('Merchandise Total')[1].strip().split(' ')[1]
        freight_total = float(summary_info[2].split(' ')[-1])
        freight_total_unit = summary_info[2].split(' ')[0]
        total_invoice = summary_info[3].split(' ')[1]
        total_invoice_unit = summary_info[3].split(' ')[0]
        init_page_values.update({
            'total_units': int(total_units) if total_units is not None else 0,
            'merchandise_total': float(merchandise_total) if merchandise_total is not None else 0.0,
            'merchandise_total_unit': str(merchandise_total_unit) if merchandise_total_unit is not None else '',
            'freight_total': float(freight_total) if freight_total is not None else 0.0,
            'freight_total_unit': str(freight_total_unit) if freight_total_unit is not None else '',
            'total_invoice': float(total_invoice) if total_invoice is not None else 0.0,
            'total_invoice_unit': str(total_invoice_unit) if total_invoice_unit is not None else ''
        })
        # Only keep keys that are columns in df_summary
        summary_row = {k: v for k, v in init_page_values.items() if k in df_summary.columns}
        df_summary = pd.concat([df_summary, pd.DataFrame([summary_row])], ignore_index=True)
    else:
        invoice_to = init_page_values['invoice_to']
        sold_to = init_page_values['sold_to']
        ship_to = init_page_values['ship_to']
        currency = init_page_values['currency']
        customer_id = init_page_values['customer_id']
        store_id = init_page_values['store_id']
        sales_order_id = init_page_values['sales_order_id']
        customer_po = init_page_values['customer_po']
        terms_str = init_page_values['terms_str']
        ship_via = init_page_values['ship_via']
        department_id = init_page_values['department_id']
        cartons_count = init_page_values['cartons_count']
        cartons_net_weight = init_page_values['cartons_net_weight']
        cartons_net_weight_unit = init_page_values['cartons_net_weight_unit']
        block3_other = block_remain.split(other_page_sep)

    # in block3_other
    # 1. use re to find indices of 157317-001 like string (6 digits + dash + 3 digits) to decide how many entries there are
    # 2. loop the # of entries, repetitively scrape below values
    # 3. the 1st group would be 1 time only until cartons_net_weight_unit
    # 4. the rest groups, start with each 157317-001 like pattern, loop until the end
    pattern_indices = [i for i, x in enumerate(block3_other) if re.search(r'\d{6}-\d{3}', x)]
    pattern_count = len(pattern_indices)

    # easy style color and descr parsing
    for cnt,i in enumerate(pattern_indices):
        style_color_idx = i # index 7
        style_color_descr_idx = i + 5 # index 12
        style_color = block3_other[style_color_idx].split('Size')[0].strip()
        style_color_descr = block3_other[style_color_descr_idx].strip()

        # Validate size - must be exactly 2 characters
        size_idx = i + 1
        size_match = re.search(r'([A-Z]{2})', block3_other[size_idx].split('Qty')[-1].strip())
        size = size_match.group(1) if size_match else None

        # easy qty parsing
        qty_idx = i + 2
        qty = int(block3_other[qty_idx])

        # Extract product_family (3 letters) and country_of_origin (2 letters) from "HBG CN Country of Origin:"
        product_country_idx = i + 3
        origin_text = block3_other[product_country_idx].split(' Country of Origin')[0].strip()
        
        # Validate product_family - must be exactly 3 uppercase letters
        product_family_match = re.search(r'^([A-Z]{3})\s+([A-Z]{2})', origin_text)
        if product_family_match:
            product_family = product_family_match.group(1)
            country_of_origin = product_family_match.group(2)
        else:
            # Check if only product family exists (3 letters)
            product_family_only_match = re.search(r'^([A-Z]{3})$', origin_text)
            if product_family_only_match:
                product_family = product_family_only_match.group(1)
                country_of_origin = None
            else:
                # Check if only country of origin exists (2 letters)
                country_only_match = re.search(r'^([A-Z]{2})$', origin_text)
                if country_only_match:
                    product_family = None
                    country_of_origin = country_only_match.group(1)
                else:
                    product_family = None
                    country_of_origin = None
        # --------------------------------------- RDS CERTIFIED BEGIN ---------------------------------------
        # rds_certified is hard to check as the string may be not in the same line
        # 1. within 100 steps, check how many more step we need to adjust
        # 2. add that offset to the index
        rdx_idx = i + 4
        rds_idx_offset = 0
        loop_total = 0
        if pattern_indices[cnt] == pattern_indices[-1]:
            loop_total = 100
        else:
            loop_total = pattern_indices[cnt+1] - pattern_indices[cnt]

        for j in range(loop_total):
            if 'Delivery #' in block3_other[rdx_idx+rds_idx_offset]:
                break
            else:
                rds_idx_offset += 1

        rds_certified_text = block3_other[rdx_idx+rds_idx_offset].split('Delivery #')[1].strip()
        rds_certified = 1 if 'RDS Certified' in rds_certified_text else 0
        # --------------------------------------- RDS CERTIFIED END ---------------------------------------

        # Extract pattern from last 12 characters: 4 digits + . + 2 digits + . + 4 digits
        tariff_code_text = block3_other[rdx_idx+rds_idx_offset].split(' Tariff code')[0].strip()
        if len(tariff_code_text) >= 12:
            last_12_chars = tariff_code_text[-12:]
            # Check if pattern matches: 4 digits + . + 2 digits + . + 4 digits
            if re.match(r'\d{4}\.\d{2}\.\d{4}$', last_12_chars):
                tariff_code = last_12_chars
            else:
                tariff_code = None
        else:
            tariff_code = None

        delivery_id = block3_other[rdx_idx+rds_idx_offset].split(' Delivery #')[0].strip()
        
        # Extract last 10 digits if they are all numbers
        delivery_id_text = block3_other[rdx_idx+rds_idx_offset].split(' Delivery #')[0].strip()
        if len(delivery_id_text) >= 10:
            last_10_chars = delivery_id_text[-10:]
            # Check if last 10 characters are all digits
            if last_10_chars.isdigit():
                delivery_id = last_10_chars
            else:
                delivery_id = None
        else:
            delivery_id = None

        other_descr_str = ''.join(block3_other[rdx_idx:rdx_idx+rds_idx_offset+1]).strip().split(' Tariff code')[0]
        other_descr = other_descr_str[:-12] if tariff_code else other_descr_str

        # need to leverage RDS logic
        price = rds_certified_text.split(' ')[-2]
        ext_price = rds_certified_text.split(' ')[-1]

        parsed_data = {
            'report_entity': report_entity,
            'transaction_date': transaction_date,
            'invoice_id': invoice_id,
            'dun_id': dun_id,
            'invoice_to': invoice_to,
            'sold_to': sold_to,
            'ship_to': ship_to,
            'currency': currency,
            'customer_id': customer_id,
            'store_id': store_id,
            'sales_order_id': sales_order_id,
            'customer_po': customer_po,
            'terms_str': terms_str,
            'ship_via': ship_via,
            'department_id': department_id,
            'cartons_count': cartons_count,
            'cartons_net_weight': cartons_net_weight,
            'cartons_net_weight_unit': cartons_net_weight_unit,
            'cartons_gross_weight': cartons_gross_weight,
            'cartons_gross_weight_unit': cartons_gross_weight_unit,
            'style_color': style_color, 
            'style_color_descr': style_color_descr,
            'size': size,
            'qty': qty,
            'product_family': product_family,
            'country_of_origin': country_of_origin,
            'rds_certified': rds_certified, 
            'tariff_code': tariff_code,
            'delivery_id': delivery_id,
            'other_descr': other_descr,
            'price': price,
            'ext_price': ext_price
        }
        df = pd.concat([df, pd.DataFrame([parsed_data])], ignore_index=True)


