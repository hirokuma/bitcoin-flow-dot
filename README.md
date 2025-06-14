# TXID から Esplora API でトランザクションを読み取って DOTファイルにする

[https://claude.ai](https://claude.ai) で生成してもらった。

> Bitcoinトランザクションのvinとvoutをまとめたテキストファイルから、それのフローを出力するdot言語に出力するコードを生成する。プログラミング言語はなんでもよい。

> TXID一覧のテキストファイルを読み取り Esplora API でトランザクションを取得し、この入力ファイル形式で出力するプログラムを作成。
> http://localhost:8094/regtest/api

## 手順

* TXID一覧のテキストファイルを作る(`txids.txt`など)
* `python esplora_fetcher.py txids.txt transactions.txt` (必要があれば `base_url` を指定する)
* `python bitcoin_flow_dot.py transactions.txt flow.dot`

できあがった dotファイルを graphviz で見る。
