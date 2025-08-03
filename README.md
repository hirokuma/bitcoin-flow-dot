# TXID から Esplora API でトランザクションを読み取って DOTファイルにする

[https://claude.ai](https://claude.ai) で生成してもらった。

> Bitcoinトランザクションのvinとvoutをまとめたテキストファイルから、それのフローを出力するdot言語に出力するコードを生成する。プログラミング言語はなんでもよい。

> TXID一覧のテキストファイルを読み取り Esplora API でトランザクションを取得し、この入力ファイル形式で出力するプログラムを作成。

## 手順

* TXID一覧のテキストファイルを作る(`txids.txt`など)
  * 特定のTXIDにラベルを付けたければ、コンマで区切って文字列を書く
  * 特定のアドレスをラベルに変換したければ、`addr_map.json` を作って編集する

```console
$ python esplora_fetcher.py txids.txt transactions.json
$ python bitcoin_flow_dot.py transactions.json bitcoin_flow.dot
```

できあがった dotファイルはビュアーで閲覧したり `dot` コマンドで画像ファイルに変換するなりできる。

```console
$ dot -Tpng bitcoin_flow.dot -o bitcoin_flow.png
```

## Help

### esplora_fetcher.py

`<txid_list_file>` のTXIDを読み取ってEsplora APIでトランザクション情報を取得し `<output_file>` に保存する。

```console
$ python esplora_fetcher.py
Usage: python esplora_fetcher.py <txid_list_file> <output_file> [options]

Options:
  --base-url URL    Esplora API base URL (default: http://localhost:3002)
  --delay SECONDS   Delay between API requests (default: 0.1)
  --format FORMAT   Output format: json|text (default: json)

Examples:
  python esplora_fetcher.py txids.txt transactions.json
  python esplora_fetcher.py txids.txt transactions.txt --format text
  python esplora_fetcher.py txids.txt data.json --base-url http://localhost:8094/regtest/api --delay 0.2
```

### bitcoin_flow_dot.py

`<input_file>` (`esplora_fetcher.py` の `<output_file>`) を読み取って Graphviz の dot ファイルに変換する。

```console
$ python bitcoin_flow_dot.py
Usage: python bitcoin_flow_viz.py <input_file> [output_file]

Input file formats supported:
1. JSON Lines: {"txid": "abc123", "vin": [...], "vout": [...]}
2. Text format: txid:abc123 vin:prev_txid:0,prev_txid2:1 vout:addr1:1.5,addr2:2.3

Example:
python bitcoin_flow_viz.py transactions.txt bitcoin_flow.dot
```
