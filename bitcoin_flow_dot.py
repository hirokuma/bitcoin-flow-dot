#!/usr/bin/env python3
"""
Bitcoin Transaction Flow to DOT Language Generator

このスクリプトは、Bitcoinトランザクションのvinとvoutの情報を含むテキストファイルから
トランザクションフローをDOT言語形式で出力します。

入力ファイル形式例:
TRANSACTION txid1
VIN prev_txid1:output_index1 value1
VIN prev_txid2:output_index2 value2
VOUT address1 value1
VOUT address2 value2

TRANSACTION txid2
VIN prev_txid3:output_index3 value3
VOUT address3 value3
"""

import re
import sys
from collections import defaultdict
from typing import Dict, List, Set, Tuple

class BitcoinTransaction:
    def __init__(self, txid: str):
        self.txid = txid
        self.vins = []  # List of (prev_txid, output_index, value)
        self.vouts = []  # List of (address, value)

class BitcoinFlowGenerator:
    def __init__(self):
        self.transactions = {}
        self.addresses = set()
        self.tx_connections = defaultdict(list)  # prev_txid -> [current_txid]

    def parse_file(self, filename: str) -> None:
        """テキストファイルからトランザクション情報を解析"""
        current_tx = None

        with open(filename, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                try:
                    if line.startswith('TRANSACTION'):
                        parts = line.split()
                        if len(parts) >= 2:
                            txid = parts[1]
                            current_tx = BitcoinTransaction(txid)
                            self.transactions[txid] = current_tx

                    elif line.startswith('VIN') and current_tx:
                        parts = line.split()
                        if len(parts) >= 3:
                            prev_output = parts[1]  # prev_txid:output_index
                            value = float(parts[2])

                            if ':' in prev_output:
                                prev_txid, output_index = prev_output.split(':', 1)
                                current_tx.vins.append((prev_txid, int(output_index), value))
                                self.tx_connections[prev_txid].append(current_tx.txid)

                    elif line.startswith('VOUT') and current_tx:
                        parts = line.split()
                        if len(parts) >= 3:
                            address = parts[1]
                            value = float(parts[2])
                            current_tx.vouts.append((address, value))
                            self.addresses.add(address)

                except (ValueError, IndexError) as e:
                    print(f"Warning: Line {line_num} parse error: {e}", file=sys.stderr)
                    continue

    def generate_dot(self, output_file: str = None) -> str:
        """DOT言語形式でフローグラフを生成"""
        dot_content = []
        dot_content.append('digraph BitcoinFlow {')
        dot_content.append('    rankdir=LR;')
        dot_content.append('    node [shape=box];')
        dot_content.append('')

        # ノードの定義
        dot_content.append('    // Transaction nodes')
        for txid, tx in self.transactions.items():
            total_in = sum(vin[2] for vin in tx.vins)
            total_out = sum(vout[1] for vout in tx.vouts)
            label = f"{txid[:8]}...\\nIn: {total_in:.4f}\\nOut: {total_out:.4f}"
            dot_content.append(f'    "{txid}" [label="{label}", style=filled, fillcolor=lightblue];')

        dot_content.append('')
        dot_content.append('    // Address nodes')
        for address in self.addresses:
            short_addr = f"{address[:8]}...{address[-8:]}" if len(address) > 20 else address
            dot_content.append(f'    "{address}" [label="{short_addr}", style=filled, fillcolor=lightgreen, shape=ellipse];')

        # エッジの定義
        dot_content.append('')
        dot_content.append('    // Transaction to transaction connections')
        for prev_txid, next_txids in self.tx_connections.items():
            if prev_txid in self.transactions:
                for next_txid in next_txids:
                    dot_content.append(f'    "{prev_txid}" -> "{next_txid}" [color=blue];')

        dot_content.append('')
        dot_content.append('    // Transaction to address connections (outputs)')
        for txid, tx in self.transactions.items():
            for address, value in tx.vouts:
                dot_content.append(f'    "{txid}" -> "{address}" [label="{value:.4f}", color=green];')

        # 可能であれば、アドレスからトランザクションへの接続も表示
        dot_content.append('')
        dot_content.append('    // Address to transaction connections (inputs)')
        address_to_tx = defaultdict(list)
        for txid, tx in self.transactions.items():
            for prev_txid, output_index, value in tx.vins:
                if prev_txid in self.transactions:
                    prev_tx = self.transactions[prev_txid]
                    if output_index < len(prev_tx.vouts):
                        source_address = prev_tx.vouts[output_index][0]
                        address_to_tx[source_address].append((txid, value))

        for address, connections in address_to_tx.items():
            for txid, value in connections:
                dot_content.append(f'    "{address}" -> "{txid}" [label="{value:.4f}", color=red, style=dashed];')

        dot_content.append('}')

        result = '\n'.join(dot_content)

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"DOT file generated: {output_file}")

        return result

def main():
    if len(sys.argv) < 2:
        print("Usage: python bitcoin_flow_dot.py <input_file> [output_file]")
        print("\nInput file format:")
        print("TRANSACTION txid1")
        print("VIN prev_txid1:output_index1 value1")
        print("VIN prev_txid2:output_index2 value2")
        print("VOUT address1 value1")
        print("VOUT address2 value2")
        print("")
        print("TRANSACTION txid2")
        print("VIN prev_txid3:output_index3 value3")
        print("VOUT address3 value3")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    generator = BitcoinFlowGenerator()

    try:
        generator.parse_file(input_file)
        print(f"Parsed {len(generator.transactions)} transactions")
        print(f"Found {len(generator.addresses)} unique addresses")

        dot_content = generator.generate_dot(output_file)

        if not output_file:
            print("\n" + "="*50)
            print("DOT LANGUAGE OUTPUT:")
            print("="*50)
            print(dot_content)
            print("\nTo visualize, save to .dot file and use:")
            print("dot -Tpng -o graph.png graph.dot")
            print("dot -Tsvg -o graph.svg graph.dot")

    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()