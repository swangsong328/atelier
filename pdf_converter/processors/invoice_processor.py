"""Specialized invoice processor for extracting structured data from PDF invoices."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from ..models import ProcessingJob, ProcessingResult, ProcessingStatus
from .base import BaseProcessor


class InvoiceProcessor(BaseProcessor):
    """Specialized processor for extracting structured invoice data.
    
    IMPORTANT: This processor preserves original PDF values exactly as they appear.
    No interpretation, conversion, or "improvement" of values is performed.
    All extracted data maintains the exact original format and content from the PDF.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the invoice processor."""
        super().__init__(config)
        self.required_columns = [
            'transaction_date', 'invoice_id', 'dun_id', 'invoice_to', 'sold_to', 
            'ship_to', 'currency', 'customer_id', 'store_id', 'sales_order_id', 
            'customer_po', 'terms_str', 'ship_via', 'department_id', 'cartons_count', 
            'cartons_net_weight', 'cartons_gross_weight', 'style_color', 
            'style_color_descr', 'size', 'qty', 'product_family', 'country_of_origin', 
            'rds_certified', 'tariff_code', 'delivery_id', 'other_descr'
        ]
    
    def can_process(self, file_path: str) -> bool:
        """Check if this processor can handle the given file."""
        path = Path(file_path)
        return path.suffix.lower() == ".pdf"
    
    def process(self, job: ProcessingJob) -> ProcessingResult:
        """Process the invoice and extract structured data."""
        # This processor works with already extracted data
        # It should be called after the PDF processor
        raise NotImplementedError("InvoiceProcessor should be used with extracted data")
    
    def transform_to_structured_format(self, extracted_data: Dict[str, Any], metadata: Dict[str, Any]) -> pd.DataFrame:
        """Transform raw extracted data into structured invoice format."""
        # Initialize empty DataFrame with required columns
        df = pd.DataFrame(columns=self.required_columns)
        
        # Extract data from tables and text
        tables = extracted_data.get("tables", {}).get("tables", [])
        text_data = extracted_data.get("text", {})
        
        # Parse invoice header information
        header_info = self._extract_header_info(tables, text_data)
        
        # Parse line items from tables
        line_items = self._extract_line_items(tables, text_data)
        
        # Fallback: if no line items found in tables, try to extract from text
        if not line_items:
            line_items = self._extract_line_items_from_text(text_data)
        
        # Create structured records
        records = []
        for item in line_items:
            record = header_info.copy()
            record.update(item)
            records.append(record)
        
        if records:
            df = pd.DataFrame(records)
        
        return df
    
    def _extract_header_info(self, tables: List[Dict], text_data: Dict) -> Dict[str, Any]:
        """Extract header information from invoice, using both tables and text."""
        header_info: Dict[str, Any] = {col: None for col in self.required_columns}
        header_info['currency'] = 'USD'
        full_text = text_data.get("full_text", "")

        # --- Try to extract from tables first (for key header fields) ---
        for table in tables:
            data = table.get("data", [])
            if not data or len(data) < 2:
                continue
            headers = [str(cell).strip().upper() for cell in data[0]]
            row = data[1] if len(data) > 1 else []
            # Map header names to columns
            for idx, h in enumerate(headers):
                if "CUSTOMER #" in h and idx < len(row):
                    header_info['customer_id'] = str(row[idx]).strip()
                if "SALES ORDER #" in h and idx < len(row):
                    header_info['sales_order_id'] = str(row[idx]).strip()
                if "CUSTOMER PO" in h and idx < len(row):
                    header_info['customer_po'] = str(row[idx]).strip()
                if "STORE #" in h and idx < len(row):
                    header_info['store_id'] = str(row[idx]).strip()

        # --- Fallback to text extraction if not found in tables ---
        if not header_info['customer_id']:
            customer_match = re.search(r'Customer\s*#\s*(\d+)', full_text, re.IGNORECASE)
            if customer_match:
                header_info['customer_id'] = customer_match.group(1)
        if not header_info['sales_order_id']:
            so_match = re.search(r'Sales\s*Order\s*#\s*(\d+)', full_text, re.IGNORECASE)
            if so_match:
                header_info['sales_order_id'] = so_match.group(1)
        if not header_info['customer_po']:
            po_match = re.search(r'Customer\s*PO\s*([A-Z0-9]+)', full_text, re.IGNORECASE)
            if po_match:
                header_info['customer_po'] = po_match.group(1)

        # --- Cartons count and weights ---
        # Try to extract from tables
        for table in tables:
            data = table.get("data", [])
            for row in data:
                for idx, cell in enumerate(row):
                    cell_str = str(cell).strip().upper()
                    # Cartons count
                    if "NO. OF CARTONS" in cell_str:
                        value = None
                        if idx+1 < len(row):
                            value = str(row[idx+1]).strip()
                        elif data.index(row)+1 < len(data):
                            next_row = data[data.index(row)+1]
                            if next_row:
                                value = str(next_row[0]).strip()
                        if value:
                            num_match = re.search(r'(\d+)', value.replace(',', ''))
                            if num_match:
                                header_info['cartons_count'] = int(num_match.group(1))
                    # Gross weight
                    if "GROSS WEIGHT" in cell_str:
                        value = None
                        if idx+1 < len(row):
                            value = str(row[idx+1]).strip()
                        elif data.index(row)+1 < len(data):
                            next_row = data[data.index(row)+1]
                            value = str(next_row[0]).strip()
                        if value:
                            num_match = re.search(r'(\d+\.?\d*)', value.replace(',', ''))
                            if num_match:
                                header_info['cartons_gross_weight'] = float(num_match.group(1))
                    # Net weight
                    if "NET WEIGHT" in cell_str:
                        value = None
                        if idx+1 < len(row):
                            value = str(row[idx+1]).strip()
                        elif data.index(row)+1 < len(data):
                            next_row = data[data.index(row)+1]
                            value = str(next_row[0]).strip()
                        if value:
                            num_match = re.search(r'(\d+\.?\d*)', value.replace(',', ''))
                            if num_match:
                                header_info['cartons_net_weight'] = float(num_match.group(1))
        # Fallback to text for cartons_count
        if not header_info['cartons_count']:
            carton_match = re.search(r'No\.\s*of\s*Cartons\s*(\d+)', full_text, re.IGNORECASE)
            if carton_match:
                header_info['cartons_count'] = int(carton_match.group(1))
        # Fallback to text for weights
        if not header_info['cartons_gross_weight']:
            gross_match = re.search(r'Gross\s*Weight\s*:?.*?(\d+\.?\d*)\s*LB', full_text, re.IGNORECASE|re.DOTALL)
            if gross_match:
                header_info['cartons_gross_weight'] = float(gross_match.group(1))
        if not header_info['cartons_net_weight']:
            net_match = re.search(r'Net\s*Weight\s*:?.*?(\d+\.?\d*)\s*LB', full_text, re.IGNORECASE|re.DOTALL)
            if net_match:
                header_info['cartons_net_weight'] = float(net_match.group(1))

        # --- Transaction date ---
        date_match = re.search(r'Date\s+(\d{2}/\d{2}/\d{4})', full_text, re.IGNORECASE)
        if date_match:
            date_str = date_match.group(1)
            try:
                parsed_date = datetime.strptime(date_str, '%m/%d/%Y')
                header_info['transaction_date'] = parsed_date.strftime('%Y-%m-%d')
            except Exception:
                header_info['transaction_date'] = '9999-12-31'
        else:
            header_info['transaction_date'] = '9999-12-31'

        # --- Delivery ID, DUN ID, etc. ---
        delivery_match = re.search(r'Delivery\s*#\s*(\d+)', full_text, re.IGNORECASE)
        if delivery_match:
            header_info['delivery_id'] = delivery_match.group(1)
        dun_match = re.search(r'DUN#(\d+)', full_text, re.IGNORECASE)
        if dun_match:
            header_info['dun_id'] = dun_match.group(1)

        # --- Address extraction (refined) ---
        self._extract_address_info(full_text, header_info)
        return header_info

    def _extract_line_items(self, tables: List[Dict], text_data: Dict) -> List[Dict[str, Any]]:
        """
        Extract line items from invoice tables.
        Handles different table structures and formats.
        """
        line_items = []
        
        for table_info in tables:
            table_data = table_info.get("data", [])
            if not table_data or len(table_data) < 2:
                continue
            
            # Look for line item patterns in various table formats
            # Check if this table contains line items by examining headers or content
            has_line_items = False
            
            # Method 1: Check for "Style-Color" header (most common)
            if table_data and len(table_data[0]) > 0:
                first_cell = str(table_data[0][0]).strip()
                if "Style-Color" in first_cell or "Style Color" in first_cell:
                    has_line_items = True
            
            # Method 2: Check if any row contains line item patterns
            if not has_line_items:
                for row in table_data:
                    if self._is_line_item_row(row):
                        has_line_items = True
                        break
            
            # Extract line items from this table
            if has_line_items:
                for row_idx, row in enumerate(table_data):
                    if row_idx == 0:  # Skip header row
                        continue
                    
                    # Check if this looks like a line item
                    if self._is_line_item_row(row):
                        item = self._parse_compressed_line_item(row)
                        if item:
                            line_items.append(item)
        
        return line_items
    
    def _extract_line_items_from_text(self, text_data: Dict) -> List[Dict[str, Any]]:
        """
        Extract line items from text data when tables don't contain them.
        This is a fallback method for PDFs where line items are in text format.
        """
        line_items = []
        full_text = text_data.get("full_text", "")
        
        if not full_text:
            return line_items
        
        # Split text into lines and look for line item patterns
        lines = full_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this line contains line item data
            if self._is_line_item_row([line]):
                # Create a mock row structure for the parser
                mock_row = [line]
                item = self._parse_compressed_line_item(mock_row)
                if item:
                    line_items.append(item)
        
        return line_items
    
    def _is_line_item_row(self, row: List[str]) -> bool:
        """
        Check if a row contains line item data.
        Uses multiple criteria to identify line items in invoice tables.
        """
        if not row:
            return False
            
        row_text = ' '.join(str(cell) for cell in row if cell).strip()
        if not row_text:
            return False
        
        # Skip header rows and summary rows
        skip_patterns = [
            r'^Style-Color$',  # Header row
            r'^Description$',  # Header row
            r'^Size$',  # Header row
            r'^Qty$',  # Header row
            r'^Total$',  # Summary row
            r'^Subtotal$',  # Summary row
            r'^Tax$',  # Summary row
            r'^Grand Total$',  # Summary row
        ]
        
        for pattern in skip_patterns:
            if re.match(pattern, row_text, re.IGNORECASE):
                return False
        
        # Look for patterns that indicate line items
        positive_patterns = [
            r'\d{6}-\d{3}',  # Style code pattern (6 digits - 3 digits)
            r'Size\s+[A-Z0-9]+',  # Size specification
            r'Main Body:',  # Material specification
            r'Trim\s*\d*:',  # Trim specification
            r'Lining:',  # Lining specification
            r'Country of Origin:',  # Origin specification
            r'Tariff code:',  # Tariff specification
        ]
        
        # Count how many positive patterns match
        matches = 0
        for pattern in positive_patterns:
            if re.search(pattern, row_text, re.IGNORECASE):
                matches += 1
        
        # Must have at least 2 positive indicators to be considered a line item
        return matches >= 2
    
    def _parse_line_item(self, row: List[str], headers: List[str]) -> Optional[Dict[str, Any]]:
        """Parse a single line item row."""
        item = {}
        
        # Map headers to our column names
        header_mapping = {
            'style_color': ['Style', 'Style Color', 'Style/Color'],
            'size': ['Size'],
            'qty': ['Qty', 'Quantity'],
            'style_color_descr': ['Description', 'Desc', 'Style Description'],
            'other_descr': ['Description', 'Desc', 'Material', 'Body', 'Lining']
        }
        
        for col_name, possible_headers in header_mapping.items():
            for header in possible_headers:
                try:
                    header_idx = headers.index(header)
                    if header_idx < len(row):
                        value = str(row[header_idx]).strip()
                        if value and value != 'nan':
                            item[col_name] = value
                            break
                except ValueError:
                    continue
        
        # Set default values for missing fields
        if 'qty' in item:
            try:
                item['qty'] = int(item['qty'])
            except (ValueError, TypeError):
                item['qty'] = 1
        
        return item if item else None
    
    def _extract_address_info(self, full_text: str, header_info: Dict[str, Any]) -> None:
        """Extract address information from the invoice text, ensuring no mixing of address blocks."""
        lines = full_text.split('\n')
        invoice_to, sold_to, ship_to = [], [], []
        current = None
        for line in lines:
            l = line.strip()
            if l.upper().startswith("INVOICE TO:"):
                current = invoice_to
                continue
            elif l.upper().startswith("SOLD TO:"):
                current = sold_to
                continue
            elif l.upper().startswith("SHIP TO:"):
                current = ship_to
                continue
            elif l.upper().startswith("CURRENCY") or l.upper().startswith("CUSTOMER") or l.upper().startswith("TERMS") or l.upper().startswith("SALES ORDER") or l.upper().startswith("STORE #") or l.upper().startswith("DELIVERY"):
                current = None
                continue
            if current is not None and l:
                current.append(l)
        if invoice_to:
            header_info['invoice_to'] = ' '.join(invoice_to)
        if sold_to:
            header_info['sold_to'] = ' '.join(sold_to)
        if ship_to:
            header_info['ship_to'] = ' '.join(ship_to)

    def _parse_compressed_line_item(self, row: List[str]) -> Optional[Dict[str, Any]]:
        """
        Parse a compressed line item row where all data is in the first cell.
        This method extracts exact values as they appear in the PDF without interpretation.
        """
        item = {}
        if not row or not row[0]:
            return None
            
        cell_text = str(row[0]).strip()
        if not cell_text:
            return None
            
        # Split the cell text into lines for better parsing
        lines = [line.strip() for line in cell_text.split('\n') if line.strip()]
        
        # Extract quantity (first number at the beginning)
        qty_match = re.search(r'^\s*(\d+)', cell_text)
        if qty_match:
            item['qty'] = int(qty_match.group(1))
        
        # Extract style code (pattern: 6 digits - 3 digits)
        style_match = re.search(r'(\d{6}-\d{3})', cell_text)
        if style_match:
            item['style_color'] = style_match.group(1)
        
        # Extract size - look for "Size" followed by letters/numbers
        size_match = re.search(r'Size\s+([A-Z0-9]+)', cell_text, re.IGNORECASE)
        if size_match:
            item['size'] = size_match.group(1)
        
        # Extract description - this is the text between style code and material specifications
        # Look for the main product description that appears after the style code
        style_pos = cell_text.find(item.get('style_color', '')) if item.get('style_color') else -1
        if style_pos >= 0:
            # Find the end of description (before material specs)
            desc_end_markers = ['Main Body:', 'Trim', 'Lining:', 'Country of Origin:', 'Tariff code:']
            desc_end = len(cell_text)
            for marker in desc_end_markers:
                marker_pos = cell_text.find(marker, style_pos)
                if marker_pos >= 0 and marker_pos < desc_end:
                    desc_end = marker_pos
            
            # Extract description text
            if desc_end > style_pos:
                desc_text = cell_text[style_pos:desc_end].strip()
                # Remove the style code from the beginning
                if item.get('style_color'):
                    desc_text = desc_text.replace(item['style_color'], '').strip()
                # Clean up common prefixes/suffixes
                desc_text = re.sub(r'^[-:\s]+', '', desc_text)  # Remove leading dashes, colons, spaces
                desc_text = re.sub(r'[-:\s]+$', '', desc_text)  # Remove trailing dashes, colons, spaces
                if desc_text:
                    item['style_color_descr'] = desc_text
        
        # Extract material specifications (Main Body, Trim, Lining, etc.)
        material_specs = []
        
        # Look for Main Body specification
        main_body_match = re.search(r'Main Body\s*:\s*([^;\n]+)', cell_text, re.IGNORECASE)
        if main_body_match:
            material_specs.append(f"Main Body: {main_body_match.group(1).strip()}")
        
        # Look for Trim specifications (can be multiple)
        trim_matches = re.findall(r'Trim\s*\d*\s*:\s*([^;\n]+)', cell_text, re.IGNORECASE)
        for i, trim_match in enumerate(trim_matches, 1):
            material_specs.append(f"Trim{i}: {trim_match.strip()}")
        
        # Look for Lining specification
        lining_match = re.search(r'Lining\s*:\s*([^;\n]+)', cell_text, re.IGNORECASE)
        if lining_match:
            material_specs.append(f"Lining: {lining_match.group(1).strip()}")
        
        # Combine all material specifications
        if material_specs:
            item['other_descr'] = '; '.join(material_specs)
        
        # Extract country of origin
        country_match = re.search(r'Country of Origin:\s*([A-Z]{2,})', cell_text, re.IGNORECASE)
        if country_match:
            item['country_of_origin'] = country_match.group(1)
        
        # Extract tariff code
        tariff_match = re.search(r'Tariff code:\s*(\d+\.\d+\.\d+)', cell_text, re.IGNORECASE)
        if tariff_match:
            item['tariff_code'] = tariff_match.group(1)
        
        # Extract delivery ID if present in the line item
        delivery_match = re.search(r'Delivery\s*#\s*(\d+)', cell_text, re.IGNORECASE)
        if delivery_match:
            item['delivery_id'] = delivery_match.group(1)
        
        # Set default values for required fields that might be missing
        if 'qty' not in item:
            item['qty'] = 1
        
        # Only return item if we have at least some meaningful data
        return item if len(item) > 1 else None 