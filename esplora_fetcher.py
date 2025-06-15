#!/usr/bin/env python3
"""
Esplora API Transaction Fetcher
Fetches Bitcoin transaction data from Esplora API and outputs in JSON Lines format
"""

import requests
import json
import sys
import time
from typing import Dict, List, Optional

class EsploraFetcher:
    def __init__(self, base_url: str = "http://localhost:8094/regtest/api"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        # Set reasonable timeouts
        self.session.timeout = 30

    def get_transaction(self, txid: str) -> Optional[Dict]:
        """
        Fetch transaction data from Esplora API
        Returns transaction data or None if failed
        """
        url = f"{self.base_url}/tx/{txid}"

        try:
            print(f"Fetching: {txid}")
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Error fetching {txid}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON for {txid}: {e}")
            return None

    def process_transaction(self, tx_data: Dict, tx_label: str) -> Dict:
        """
        Process raw Esplora transaction data into our format
        """
        txid = tx_data.get('txid', '')

        # Process inputs (vin)
        vin = []
        for input_data in tx_data.get('vin', []):
            try:
                if 'txid' in input_data and input_data['txid']:
                    # Regular input
                    vin.append({
                        'txid': input_data['txid'],
                        'vout': input_data.get('vout', 0)
                    })
                else:
                    # Coinbase input or missing txid
                    vin.append({
                        'txid': 'coinbase',
                        'vout': 0
                    })
            except Exception as e:
                print(f"Warning: Error processing vin for {txid}: {e}")
                # Add a fallback coinbase entry
                vin.append({
                    'txid': 'coinbase',
                    'vout': 0
                })

        # Process outputs (vout)
        vout = []
        for i, output_data in enumerate(tx_data.get('vout', [])):
            try:
                address = output_data.get('scriptpubkey_address', f"output_{i}")
                vout_entry = {
                    'n': i,
                    'value': output_data.get('value', 0),
                    'address': address # Use raw address
                }

                vout.append(vout_entry)

            except Exception as e:
                print(f"Warning: Error processing vout {i} for {txid}: {e}")
                # Add a fallback entry
                vout.append({
                    'n': i,
                    'value': 0.0,
                    'address': f"error_output_{i}"
                })

        return {
            'txid': txid,
            'tx_label': tx_label,
            'vin': vin,
            'vout': vout
        }

    def read_txid_list(self, filename: str) -> List[str]:
        """
        Read TXID list from file
        Each line should contain one TXID
        """
        txids = []
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Remove any extra whitespace and validate format
                        l = line.split(',')
                        label = ''
                        if len(l) == 2:
                            label = l[1]
                        txid = l[0]  # Take first word if multiple
                        if len(txid) == 64:  # Bitcoin TXID is 64 hex characters
                            txids.append({'txid': txid, 'label': label})
                        else:
                            print(f"Warning: Invalid TXID format: {txid}")

            print(f"Found {len(txids)} valid TXIDs in {filename}")
            return txids

        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
            sys.exit(1)

    def fetch_all_transactions(self, txids: List[str], delay: float = 0.1) -> List[Dict]:
        """
        Fetch all transactions with optional delay between requests
        """
        transactions = []
        total = len(txids)

        for i, txid in enumerate(txids):
            print(f"Progress: {i+1}/{total}")

            tx_data = self.get_transaction(txid.get('txid'))
            if tx_data:
                processed_tx = self.process_transaction(tx_data, txid.get('label', ''))
                transactions.append(processed_tx)

            # Add delay to avoid overwhelming the API
            if delay > 0 and i < total - 1:
                time.sleep(delay)

        print(f"Successfully fetched {len(transactions)} transactions")
        return transactions

    def save_json_lines(self, transactions: List[Dict], output_file: str):
        """
        Save transactions in JSON Lines format
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for tx in transactions:
                    json.dump(tx, f, separators=(',', ':'))
                    f.write('\n')

            print(f"Transactions saved to: {output_file}")

        except Exception as e:
            print(f"Error saving file: {e}")
            sys.exit(1)

    def save_text_format(self, transactions: List[Dict], output_file: str):
        """
        Save transactions in simple text format
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for tx in transactions:
                    txid = tx['txid']

                    # Format vin
                    vin_parts = []
                    for vin in tx['vin']:
                        if vin['txid'] == 'coinbase':
                            vin_parts.append('coinbase')
                        else:
                            vin_parts.append(f"{vin['txid']}:{vin['vout']}")
                    vin_str = ','.join(vin_parts) if vin_parts else 'coinbase'

                    # Format vout
                    vout_parts = []
                    for vout in tx['vout']:
                        addr = vout.get('address', 'unknown')
                        vout_parts.append(f"{addr}:{vout['value']}")
                    vout_str = ','.join(vout_parts)

                    f.write(f"txid:{txid} vin:{vin_str} vout:{vout_str}\n")

            print(f"Transactions saved to: {output_file}")

        except Exception as e:
            print(f"Error saving file: {e}")
            sys.exit(1)

def main():
    if len(sys.argv) < 3:
        print("Usage: python esplora_fetcher.py <txid_list_file> <output_file> [options]")
        print("")
        print("Options:")
        print("  --base-url URL    Esplora API base URL (default: http://localhost:8094/regtest/api)")
        print("  --delay SECONDS   Delay between API requests (default: 0.1)")
        print("  --format FORMAT   Output format: json|text (default: json)")
        print("")
        print("Examples:")
        print("  python esplora_fetcher.py txids.txt transactions.json")
        print("  python esplora_fetcher.py txids.txt transactions.txt --format text")
        print("  python esplora_fetcher.py txids.txt data.json --base-url http://localhost:8094/regtest/api --delay 0.2")
        sys.exit(1)

    txid_file = sys.argv[1]
    output_file = sys.argv[2]

    # Parse options
    base_url = "http://localhost:8094/regtest/api"
    delay = 0.1
    output_format = "json"

    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == "--base-url" and i + 1 < len(sys.argv):
            base_url = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--delay" and i + 1 < len(sys.argv):
            try:
                delay = float(sys.argv[i + 1])
            except ValueError:
                print("Error: Invalid delay value")
                sys.exit(1)
            i += 2
        elif sys.argv[i] == "--format" and i + 1 < len(sys.argv):
            output_format = sys.argv[i + 1]
            if output_format not in ['json', 'text']:
                print("Error: Format must be 'json' or 'text'")
                sys.exit(1)
            i += 2
        else:
            print(f"Error: Unknown option {sys.argv[i]}")
            sys.exit(1)

    # Initialize fetcher
    fetcher = EsploraFetcher(base_url)

    print(f"Using Esplora API: {base_url}")
    print(f"Request delay: {delay} seconds")
    print(f"Output format: {output_format}")
    print("")

    # Read TXID list
    txids = fetcher.read_txid_list(txid_file)
    if not txids:
        print("No valid TXIDs found in input file")
        sys.exit(1)

    # Fetch transactions
    transactions = fetcher.fetch_all_transactions(txids, delay)

    if not transactions:
        print("No transactions were successfully fetched")
        sys.exit(1)

    # Save results
    if output_format == "json":
        fetcher.save_json_lines(transactions, output_file)
    else:
        fetcher.save_text_format(transactions, output_file)

    print(f"\nReady to visualize with:")
    print(f"python bitcoin_flow_dot.py {output_file}")

if __name__ == "__main__":
    main()