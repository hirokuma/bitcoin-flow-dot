#!/usr/bin/env python3
"""
Esplora API Transaction Fetcher

TXID一覧のテキストファイルを読み取り、Esplora APIからトランザクション情報を取得して
Bitcoin Flow DOT Generator用の形式で出力するプログラム

使用方法:
python esplora_fetcher.py txid_list.txt [output.txt]
"""

import requests
import json
import sys
import time
from typing import Dict, List, Optional

class EsploraClient:
    def __init__(self, base_url: str = "http://localhost:8094/regtest/api"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        # リクエスト間隔の制御用
        self.request_delay = 0.1  # 100ms

    def get_transaction(self, txid: str) -> Optional[Dict]:
        """指定されたTXIDのトランザクション情報を取得"""
        url = f"{self.base_url}/tx/{txid}"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            time.sleep(self.request_delay)  # レート制限対策
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching transaction {txid}: {e}", file=sys.stderr)
            return None
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON for transaction {txid}: {e}", file=sys.stderr)
            return None

    def get_transaction_output_addresses(self, txid: str, vout_index: int) -> Optional[str]:
        """指定されたトランザクションの出力アドレスを取得"""
        tx_data = self.get_transaction(txid)
        if not tx_data or 'vout' not in tx_data:
            return None

        if vout_index >= len(tx_data['vout']):
            return None

        vout = tx_data['vout'][vout_index]
        if 'scriptpubkey_address' in vout:
            return vout['scriptpubkey_address']
        elif 'scriptpubkey_addresses' in vout and vout['scriptpubkey_addresses']:
            return vout['scriptpubkey_addresses'][0]  # 最初のアドレスを返す
        else:
            # アドレスが取得できない場合はscriptの種類を返す
            script_type = vout.get('scriptpubkey_type', 'unknown')
            return f"[{script_type}]"

class TransactionProcessor:
    def __init__(self, esplora_client: EsploraClient):
        self.client = esplora_client

    def satoshi_to_btc(self, satoshi: int) -> float:
        """SatoshiをBTCに変換"""
        return satoshi / 100000000.0

    def process_txid_list(self, input_file: str) -> List[str]:
        """TXIDファイルを読み込んでトランザクション情報を処理"""
        output_lines = []

        # TXIDファイルを読み込み
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                txids = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        except FileNotFoundError:
            print(f"Error: File '{input_file}' not found", file=sys.stderr)
            return []
        except Exception as e:
            print(f"Error reading file '{input_file}': {e}", file=sys.stderr)
            return []

        print(f"Processing {len(txids)} transactions...")

        for i, txid in enumerate(txids, 1):
            print(f"Fetching transaction {i}/{len(txids)}: {txid}")

            tx_data = self.client.get_transaction(txid)
            if not tx_data:
                print(f"Warning: Could not fetch transaction {txid}", file=sys.stderr)
                continue

            output_lines.append(f"TRANSACTION {txid}")

            # VIN処理
            if 'vin' in tx_data:
                for vin in tx_data['vin']:
                    if 'txid' in vin and 'vout' in vin:
                        prev_txid = vin['txid']
                        prev_vout = vin['vout']

                        # 前のトランザクションの出力値を取得
                        if 'prevout' in vin and 'value' in vin['prevout']:
                            value_satoshi = vin['prevout']['value']
                            value_btc = self.satoshi_to_btc(value_satoshi)
                        else:
                            # prevoutが無い場合は前のトランザクションから取得を試みる
                            prev_tx = self.client.get_transaction(prev_txid)
                            if prev_tx and 'vout' in prev_tx and prev_vout < len(prev_tx['vout']):
                                value_satoshi = prev_tx['vout'][prev_vout]['value']
                                value_btc = self.satoshi_to_btc(value_satoshi)
                            else:
                                value_btc = 0.0
                                print(f"Warning: Could not get input value for {txid}", file=sys.stderr)

                        output_lines.append(f"VIN {prev_txid}:{prev_vout} {value_btc:.8f}")
                    elif 'coinbase' in vin:
                        # Coinbase transaction
                        output_lines.append("VIN coinbase:0 0.0")

            # VOUT処理
            if 'vout' in tx_data:
                for vout in tx_data['vout']:
                    value_satoshi = vout.get('value', 0)
                    value_btc = self.satoshi_to_btc(value_satoshi)

                    # アドレス取得
                    if 'scriptpubkey_address' in vout:
                        address = vout['scriptpubkey_address']
                    elif 'scriptpubkey_addresses' in vout and vout['scriptpubkey_addresses']:
                        address = vout['scriptpubkey_addresses'][0]
                    else:
                        # アドレスが取得できない場合
                        script_type = vout.get('scriptpubkey_type', 'unknown')
                        script_hex = vout.get('scriptpubkey', '')[:20] + ('...' if len(vout.get('scriptpubkey', '')) > 20 else '')
                        address = f"[{script_type}:{script_hex}]"

                    output_lines.append(f"VOUT {address} {value_btc:.8f}")

            output_lines.append("")  # トランザクション間の空行

        return output_lines

def main():
    if len(sys.argv) < 2:
        print("Usage: python esplora_fetcher.py <txid_list_file> [output_file] [esplora_url]")
        print("\nTXID list file format:")
        print("txid1")
        print("txid2")
        print("txid3")
        print("# コメント行は無視されます")
        print("\nDefault Esplora URL: http://localhost:8094/regtest/api")
        print("\nExample:")
        print("python esplora_fetcher.py txids.txt transactions.txt")
        print("python esplora_fetcher.py txids.txt transactions.txt http://localhost:8094/mainnet/api")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    esplora_url = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:8094/regtest/api"

    # Esploraクライアント初期化
    client = EsploraClient(esplora_url)
    processor = TransactionProcessor(client)

    print(f"Using Esplora API: {esplora_url}")

    # トランザクション情報を処理
    output_lines = processor.process_txid_list(input_file)

    if not output_lines:
        print("No transactions processed successfully")
        sys.exit(1)

    # 結果を出力
    result = '\n'.join(output_lines)

    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"\nTransaction data saved to: {output_file}")
            print(f"Processed {len([line for line in output_lines if line.startswith('TRANSACTION')])} transactions")
        except Exception as e:
            print(f"Error writing to file '{output_file}': {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("\n" + "="*50)
        print("TRANSACTION DATA OUTPUT:")
        print("="*50)
        print(result)

    print(f"\nYou can now use this output with the Bitcoin Flow DOT Generator:")
    print(f"python bitcoin_flow_dot.py {output_file if output_file else 'output.txt'} flow.dot")

if __name__ == "__main__":
    main()