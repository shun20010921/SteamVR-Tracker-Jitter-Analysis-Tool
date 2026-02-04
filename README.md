# SteamVR Tracker Jitter Analysis Tool

VRトラッカーのジッタ（位置の跳ね）をリアルタイムで可視化・解析するツールです。  
ベースステーション(BS)を1台ずつオン/オフし、どのBSがジッタの原因か特定できます。

## Features

- 🔌 SteamVR自動接続・トラッカー検出
- 📈 x, y, z座標のリアルタイムグラフ表示
- 📊 直近100サンプルの標準偏差(σ)をリアルタイム計算
- 💾 CSV出力（MATLAB互換形式）
- 🎨 トラッカーごとに色分け表示

## Requirements

- Python 3.10+
- SteamVR
- VIVE Tracker

## Installation

```bash
pip install -r requirements.txt
```

## Usage

1. SteamVRを起動（トラッカーを接続）
2. ツールを起動

```bash
python main.py
```

3. 「Connect to SteamVR」をクリック
4. 「Start Measurement」で計測開始
5. BSをオン/オフしてσ値の変化を観察
6. 「Save CSV」でデータ保存

## CSV Format

```csv
timestamp,tracker_id,x,y,z,sigma_x,sigma_y,sigma_z
1707048000.123,LHR-XXXXX,0.500000,1.200000,-0.300000,0.001234,0.002345,0.001567
```

## Screenshot

```
┌─────────────────────────────────────────────────────────┐
│  SteamVR Tracker Jitter Analysis                        │
├─────────────────────────────────────────────────────────┤
│  [▶ Start] [■ Stop] [💾 Save CSV]                       │
├─────────────────────────────────────────────────────────┤
│  Tracker 1 (LHR-XXXXXX)  σx: 0.0012  σy: 0.0008        │
│  ┌───────────────────────────────────────────────┐      │
│  │  X ─────────  Y ─────────  Z ─────────        │      │
│  └───────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────┘
```

## License

MIT
