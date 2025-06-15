#!/usr/bin/env python3
"""
Bitcoin Transaction Flow Visualizer
Generates DOT language output from Bitcoin transaction vin/vout data
"""

import json
import sys
from collections import defaultdict
from typing import Dict, List, Set

class BitcoinFlowVisualizer:
    def __init__(self):
        self.transactions = {}
        self.edges = []
        self.addr_map = {}
        self._load_addr_map_from_file()

    def _load_addr_map_from_file(self, filename: str = "addr_map.json"):
        """Load address map from a JSON file if it exists."""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.addr_map.update(data)
                print(f"Loaded address map from {filename}")
        except FileNotFoundError:
            print(f"Info: '{filename}' not found. Address labels will be shortened if not in default map.")
        except json.JSONDecodeError as e:
            print(f"Error: Could not decode '{filename}': {e}. Address labels will be shortened.")

    def convert_address(self, address: str) -> str:
        """Converts a Bitcoin address to a predefined label or a shortened version."""
        if not address: # Handle cases where address might be None or empty
            return "unknown_address"
        addr = self.addr_map.get(address)
        if addr is None:
            addr = f"{address[:4]}...{address[-4:]}"
        return addr

    def parse_transaction_file(self, filename: str):
        """
        Parse transaction data from text file
        Expected format (JSON lines or structured text):
        {"txid": "abc123", "vin": [...], "vout": [...]}
        """
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    try:
                        # Try parsing as JSON
                        tx_data = json.loads(line)
                        self.process_transaction(tx_data)
                    except json.JSONDecodeError:
                        # Try parsing as structured text
                        self.parse_text_format(line)

        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
            sys.exit(1)

    def parse_text_format(self, line: str):
        """
        Parse simple text format:
        txid:abc123 vin:prev_txid:0,prev_txid2:1 vout:addr1:amount1,addr2:amount2
        """
        parts = line.split(' ')
        tx_data = {'vin': [], 'vout': []}

        for part in parts:
            if part.startswith('txid:'):
                tx_data['txid'] = part[5:]
            elif part.startswith('vin:'):
                vin_str = part[4:]
                if vin_str and vin_str != 'coinbase':
                    for vin_item in vin_str.split(','):
                        if ':' in vin_item:
                            prev_txid, vout_idx = vin_item.split(':', 1)
                            tx_data['vin'].append({
                                'txid': prev_txid,
                                'vout': int(vout_idx)
                            })
            elif part.startswith('vout:'):
                vout_str = part[5:]
                if vout_str:
                    for i, vout_item in enumerate(vout_str.split(',')):
                        if ':' in vout_item:
                            addr, amount = vout_item.split(':', 1)
                            tx_data['vout'].append({
                                'n': i,
                                'address': addr,
                                'value': float(amount)
                            })

        if 'txid' in tx_data:
            self.process_transaction(tx_data)

    def process_transaction(self, tx_data: Dict):
        """Process a single transaction"""
        txid = tx_data.get('txid', '')
        if not txid:
            return

        # Store transaction data
        self.transactions[txid] = {
            'vin': tx_data.get('vin', []),
            'vout': tx_data.get('vout', []),
            'tx_label': tx_data.get('tx_label'),
        }

        # Create edges from inputs to this transaction
        for vin in tx_data.get('vin', []):
            if 'txid' in vin and vin['txid'] != 'coinbase':
                prev_txid = vin['txid']
                prev_vout = vin.get('vout', 0)
                self.edges.append((prev_txid, prev_vout, txid))

    def generate_node_label(self, txid: str) -> str:
        """Generate node label in the specified format"""
        tx = self.transactions.get(txid, {'vin': [], 'vout': []})

        # Generate input ports
        vin_parts = []
        for i, vin in enumerate(tx['vin']):
            vin_parts.append(f"<in{i}>in#{i}")

        # Generate output ports
        vout_parts = []
        for i, vout in enumerate(tx['vout']):
            raw_addr = vout.get('address')
            converted_addr = self.convert_address(raw_addr)
            value = '{:,}'.format(int(vout.get('value')))
            vout_parts.append(f"<out{i}>#{i} {converted_addr}: {value}\\l")

        # Construct label
        vin_section = "|".join(vin_parts) if vin_parts else ""
        vout_section = "|".join(vout_parts) if vout_parts else ""

        # transaction label
        if len(tx['tx_label']) != 0:
            txid = f"{txid}\\n{tx['tx_label']}"

        if vin_section and vout_section:
            label = f"{txid}|{{{vin_section}|{{{vout_section}}}}}"
        elif vin_section:
            label = f"{txid}|{{{vin_section}}}"
        elif vout_section:
            label = f"{txid}|{{{vout_section}}}"
        else:
            label = txid

        return label

    def generate_dot(self) -> str:
        """Generate DOT language output"""
        dot_lines = [
            "digraph bitcoin_flow {",
            "    rankdir=LR;",
            "    graph [fontname=\"monospace\"];",
            "    node [shape=record, fontname=\"monospace\", fontsize=10];",
            "    edge [fontname=\"Arial\", fontsize=8];",
            ""
        ]

        # Add nodes
        for txid in self.transactions:
            label = self.generate_node_label(txid)
            # Escape special characters in DOT
            escaped_label = label   # .replace('"', '\\"').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('<', '\\<').replace('>', '\\>')
            dot_lines.append(f'    "{txid}" [label="{escaped_label}"];')

        dot_lines.append("")

        # Add edges
        for prev_txid, prev_vout, curr_txid in self.edges:
            if prev_txid in self.transactions and curr_txid in self.transactions:
                # Find the input index in current transaction
                curr_tx = self.transactions[curr_txid]
                input_idx = 0
                for i, vin in enumerate(curr_tx['vin']):
                    if vin.get('txid') == prev_txid and vin.get('vout') == prev_vout:
                        input_idx = i
                        break

                dot_lines.append(f'    "{prev_txid}":out{prev_vout} -> "{curr_txid}":in{input_idx};')

        dot_lines.extend([
            "",
            "}"
        ])

        return "\n".join(dot_lines)

    def save_dot_file(self, output_filename: str):
        """Save DOT output to file"""
        dot_content = self.generate_dot()
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(dot_content)
        print(f"DOT file saved as: {output_filename}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python bitcoin_flow_viz.py <input_file> [output_file]")
        print("")
        print("Input file formats supported:")
        print("1. JSON Lines: {\"txid\": \"abc123\", \"vin\": [...], \"vout\": [...]}")
        print("2. Text format: txid:abc123 vin:prev_txid:0,prev_txid2:1 vout:addr1:1.5,addr2:2.3")
        print("")
        print("Example:")
        print("python bitcoin_flow_viz.py transactions.txt bitcoin_flow.dot")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "bitcoin_flow.dot"

    visualizer = BitcoinFlowVisualizer()

    print(f"Parsing transactions from: {input_file}")
    visualizer.parse_transaction_file(input_file)

    print(f"Found {len(visualizer.transactions)} transactions")
    print(f"Found {len(visualizer.edges)} connections")

    visualizer.save_dot_file(output_file)
    print(f"To visualize: dot -Tpng {output_file} -o bitcoin_flow.png")

if __name__ == "__main__":
    main()