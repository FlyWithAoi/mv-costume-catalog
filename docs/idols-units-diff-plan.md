# idols.json / units.json 追加差分案

`public/data/idols.json` / `public/data/units.json` を、あんさんぶるスターズ！！Music の全アイドル（60キャラ想定）・必須ユニット18件に近づけるための追加差分案です。

このドキュメントは**計画・差分案のみ**です。この文書の追加によって `idols.json` / `units.json` / コード / 画像 / `_private` は一切変更していません。

対象コミット基準: `b45297a docs: add raw screenshots migration plan`

声優名は含めていません。キャラクター名・読み・所属のみを対象にしています。

---

## 0. 全体方針（先に読んでください）

### sort_order の扱いについて

既存の登録は3ユニット・12アイドルのみで、`sort_order` は以下のように**飛び飛び**です。

- fine: 10 / 20 / 30 / 40
- UNDEAD: 110 / 120 / 130 / 140
- Ra*bits: 200 / 210 / 220 / 230

このままの数値に、残り15ユニット・48アイドルを事務所順・ユニット順を保って割り込ませようとすると、隙間が狭すぎる箇所（特に UNDEAD の70〜Ra*bitsの80の間に紅月・MELLOW DEAR USを割り込ませる等）が発生し、将来さらに追加するときの余白がなくなります。

そのため、本ドキュメントでは以下の2案を提示します。

- **案A（推奨）**: ユニット単位で基準値を100刻みに置き直し、アイドルは「ユニット基準値 + 10刻み」で再採番する。相対的な順序（事務所順・ユニット内順）は変えず、数値だけを整理し直す。将来の追加余地を広く確保できる。
- **案B（最小変更）**: 既存の3ユニット・12アイドルの `sort_order` はそのまま変更せず、隙間に新規分を詰め込む。数値が不揃いになり、将来の追加余地が乏しい。

**案Aを推奨します。** 以降の表は案Aの数値で記載し、既存分の変更点は「状態」列に明記します。案Bが必要な場合は3章末に補足します。

### unit_type について

`app.js` を確認したところ、現状 `unit_type` フィールドはコード側で参照されていません（表示・フィルターに影響しない、純粋なメタデータ）。そのため新しい値（`cross` / `teacher` など）を追加しても表示は壊れませんが、実際に使う値の設計は別途の判断が必要です（4章参照）。

---

## 1. idol 追加・更新差分案

事務所・ユニット順に記載。`状態`が「既存」のものは12件、それ以外48件は追加案です。

### STARMAKER PRODUCTION

#### fine（既存ユニット、メンバー変更なし）

| slug | name | name_kana | name_romaji | aliases案 | sort_order案 | unit | 状態 | 備考 |
|---|---|---|---|---|---|---|---|---|
| tenshouin-eichi | 天祥院 英智 | てんしょういん えいち | tenshouin eichi | ["英智","eichi"] | 110 | fine | 既存（sort_order変更） | 現行10→110（案A） |
| hibiki-wataru | 日々樹 渉 | ひびき わたる | hibiki wataru | ["渉","wataru"] | 120 | fine | 既存（sort_order変更） | 現行20→120 |
| himemiya-tori | 姫宮 桃李 | ひめみや とうり | himemiya tori | ["桃李","tori"] | 130 | fine | 既存（sort_order変更） | 現行30→130 |
| fushimi-yuzuru | 伏見 弓弦 | ふしみ ゆづる | fushimi yuzuru | ["弓弦","yuzuru"] | 140 | fine | 既存（sort_order変更） | 現行40→140 |

#### Trickstar（追加ユニット）

| slug | name | name_kana | name_romaji | aliases案 | sort_order案 | unit | 状態 | 備考 |
|---|---|---|---|---|---|---|---|---|
| hidaka-hokuto | 氷鷹 北斗 | ひだか ほくと | hidaka hokuto | ["北斗","hokuto"] | 210 | Trickstar | 追加 | |
| akehoshi-subaru | 明星 スバル | あけほし すばる | akehoshi subaru | ["スバル","subaru"] | 220 | Trickstar | 追加 | |
| yuuki-makoto | 遊木 真 | ゆうき まこと | yuuki makoto | ["真","makoto"] | 230 | Trickstar | 追加 | ローマ字の長音表記（yuuki/yuki）要確認 |
| isara-mao | 衣更 真緒 | いさら まお | isara mao | ["真緒","mao"] | 240 | Trickstar | 追加 | |

#### 流星隊（追加ユニット）

| slug | name | name_kana | name_romaji | aliases案 | sort_order案 | unit | 状態 | 備考 |
|---|---|---|---|---|---|---|---|---|
| nagumo-tetora | 南雲 鉄虎 | なぐも てとら | nagumo tetora | ["鉄虎","tetora"] | 310 | 流星隊 | 追加 | |
| takamine-midori | 高峯 翠 | たかみね みどり | takamine midori | ["翠","midori"] | 320 | 流星隊 | 追加 | |
| sengoku-shinobu | 仙石 忍 | せんごく しのぶ | sengoku shinobu | ["忍","shinobu"] | 330 | 流星隊 | 追加 | |
| morisawa-chiaki | 守沢 千秋 | もりさわ ちあき | morisawa chiaki | ["千秋","chiaki"] | 340 | 流星隊 | 追加 | |
| shinkai-kanata | 深海 奏汰 | しんかい かなた | shinkai kanata | ["奏汰","kanata"] | 350 | 流星隊 | 追加 | |

#### ALKALOID（追加ユニット）

| slug | name | name_kana | name_romaji | aliases案 | sort_order案 | unit | 状態 | 備考 |
|---|---|---|---|---|---|---|---|---|
| amagi-hiiro | 天城 一彩 | あまぎ ひいろ | amagi hiiro | ["一彩","hiiro"] | 410 | ALKALOID | 追加 | Crazy:Bの天城燐音と兄弟（天城一彩が弟、天城燐音が兄） |
| shiratori-aira | 白鳥 藍良 | しらとり あいら | shiratori aira | ["藍良","aira"] | 420 | ALKALOID | 追加 | |
| ayase-mayoi | 礼瀬 マヨイ | あやせ まよい | ayase mayoi | ["マヨイ","mayoi"] | 430 | ALKALOID | 追加 | |
| kazehaya-tatsumi | 風早 巽 | かぜはや たつみ | kazehaya tatsumi | ["巽","tatsumi"] | 440 | ALKALOID | 追加 | |

### COSMIC PRODUCTION

#### Eden（追加ユニット）

| slug | name | name_kana | name_romaji | aliases案 | sort_order案 | unit | 状態 | 備考 |
|---|---|---|---|---|---|---|---|---|
| ran-nagisa | 乱 凪砂 | らん なぎさ | ran nagisa | ["凪砂","nagisa"] | 510 | Eden | 追加 | |
| tomoe-hiyori | 巴 日和 | ともえ ひより | tomoe hiyori | ["日和","hiyori"] | 520 | Eden | 追加 | |
| saegusa-ibara | 七種 茨 | さえぐさ いばら | saegusa ibara | ["茨","ibara"] | 530 | Eden | 追加 | |
| sazanami-jun | 漣 ジュン | さざなみ じゅん | sazanami jun | ["ジュン","jun"] | 540 | Eden | 追加 | |

#### Valkyrie（追加ユニット）

| slug | name | name_kana | name_romaji | aliases案 | sort_order案 | unit | 状態 | 備考 |
|---|---|---|---|---|---|---|---|---|
| itsuki-shu | 斎宮 宗 | いつき しゅう | itsuki shu | ["宗","shu"] | 610 | Valkyrie | 追加 | 長音表記（shu/shuu）要確認 |
| kagehira-mika | 影片 みか | かげひら みか | kagehira mika | ["みか","mika"] | 620 | Valkyrie | 追加 | |

#### 2wink（追加ユニット）

| slug | name | name_kana | name_romaji | aliases案 | sort_order案 | unit | 状態 | 備考 |
|---|---|---|---|---|---|---|---|---|
| aoi-hinata | 葵 ひなた | あおい ひなた | aoi hinata | ["ひなた","hinata"] | 710 | 2wink | 追加 | 葵ゆうたと双子（葵ひなたが兄、葵ゆうたが弟） |
| aoi-yuuta | 葵 ゆうた | あおい ゆうた | aoi yuuta | ["ゆうた","yuuta"] | 720 | 2wink | 追加 | 葵ひなたと双子（葵ひなたが兄、葵ゆうたが弟）。長音表記（yuuta/yuta）要確認 |

#### Crazy:B（追加ユニット）

| slug | name | name_kana | name_romaji | aliases案 | sort_order案 | unit | 状態 | 備考 |
|---|---|---|---|---|---|---|---|---|
| amagi-rinne | 天城 燐音 | あまぎ りんね | amagi rinne | ["燐音","rinne"] | 810 | Crazy:B | 追加 | ALKALOIDの天城一彩と兄弟（天城燐音が兄、天城一彩が弟） |
| himeru | HiMERU | ひめる | himeru | [] | 820 | Crazy:B | 追加 | 表示名は指定どおり「HiMERU」、slugは「himeru」（指定どおり） |
| oukawa-kohaku | 桜河 こはく | おうかわ こはく | oukawa kohaku | ["こはく","kohaku"] | 830 | Crazy:B | 追加 | Double Face兼任（5章参照） |
| shiina-niki | 椎名 ニキ | しいな にき | shiina niki | ["ニキ","niki"] | 840 | Crazy:B | 追加 | |

### Rhythm Link

#### UNDEAD（既存ユニット、メンバー変更なし）

| slug | name | name_kana | name_romaji | aliases案 | sort_order案 | unit | 状態 | 備考 |
|---|---|---|---|---|---|---|---|---|
| sakuma-rei | 朔間 零 | さくま れい | sakuma rei | ["零","rei"] | 910 | UNDEAD | 既存（sort_order変更） | 現行110→910。Knightsの朔間凛月と兄弟（朔間零が兄、朔間凛月が弟） |
| hakaze-kaoru | 羽風 薫 | はかぜ かおる | hakaze kaoru | ["薫","kaoru"] | 920 | UNDEAD | 既存（sort_order変更） | 現行120→920 |
| oogami-koga | 大神 晃牙 | おおがみ こうが | oogami koga | ["晃牙","koga"] | 930 | UNDEAD | 既存（sort_order変更） | 現行130→930 |
| otogari-adonis | 乙狩 アドニス | おとがり あどにす | otogari adonis | ["アドニス","adonis"] | 940 | UNDEAD | 既存（sort_order変更） | 現行140→940 |

#### Ra*bits（既存ユニット、メンバー変更なし）

| slug | name | name_kana | name_romaji | aliases案 | sort_order案 | unit | 状態 | 備考 |
|---|---|---|---|---|---|---|---|---|
| nito-nazuna | 仁兎 なずな | にと なずな | nito nazuna | ["なずな","nazuna"] | 1010 | Ra*bits | 既存（sort_order変更） | 現行200→1010（既存ファイル内の並び順を維持） |
| shino-hajime | 紫之 創 | しの はじめ | shino hajime | ["創","hajime"] | 1020 | Ra*bits | 既存（sort_order変更） | 現行210→1020 |
| mashiro-tomoya | 真白 友也 | ましろ ともや | mashiro tomoya | ["友也","tomoya"] | 1030 | Ra*bits | 既存（sort_order変更） | 現行220→1030 |
| tenma-mitsuru | 天満 光 | てんま みつる | tenma mitsuru | ["光","mitsuru"] | 1040 | Ra*bits | 既存（sort_order変更） | 現行230→1040 |

#### 紅月（追加ユニット）

| slug | name | name_kana | name_romaji | aliases案 | sort_order案 | unit | 状態 | 備考 |
|---|---|---|---|---|---|---|---|---|
| hasumi-keito | 蓮巳 敬人 | はすみ けいと | hasumi keito | ["敬人","keito"] | 1110 | 紅月 | 追加 | |
| kiryuu-kurou | 鬼龍 紅郎 | きりゅう くろう | kiryuu kurou | ["紅郎","kurou"] | 1120 | 紅月 | 追加 | 長音表記（kiryuu/kiryu, kurou/kuro）要確認 |
| kanzaki-souma | 神崎 颯馬 | かんざき そうま | kanzaki souma | ["颯馬","souma"] | 1130 | 紅月 | 追加 | 長音表記（souma/soma）要確認 |
| taki-ibuki | 滝 維吹 | たき いぶき | taki ibuki | ["維吹","ibuki"] | 1140 | 紅月 | 追加 | 紅月加入メンバーとして扱う（指定どおり） |

#### MELLOW DEAR US（追加ユニット）

| slug | name | name_kana | name_romaji | aliases案 | sort_order案 | unit | 状態 | 備考 |
|---|---|---|---|---|---|---|---|---|
| kojika-juisu | 小鹿 ジュイス | こじか じゅいす | kojika juisu | ["ジュイス","juisu"] | 1210 | MELLOW DEAR US | 追加 | カタカナ名の英語表記（Juice等）要確認 |
| madoka-nozomi | 円果 望見 | まどか のぞみ | madoka nozomi | ["望見","nozomi"] | 1220 | MELLOW DEAR US | 追加 | |
| kuon-mashu | 久遠 舞珠 | くおん ましゅ | kuon mashu | ["舞珠","mashu"] | 1230 | MELLOW DEAR US | 追加 | |
| tsuzura-chitose | 甘楽 チトセ | つづら ちとせ | tsuzura chitose | ["チトセ","chitose"] | 1240 | MELLOW DEAR US | 追加 | 英語表記 Chitose Tsuzura を参考に、tsuzura-chitose で扱う |

### NEW DIMENSION

#### Knights（追加ユニット）

| slug | name | name_kana | name_romaji | aliases案 | sort_order案 | unit | 状態 | 備考 |
|---|---|---|---|---|---|---|---|---|
| suou-tsukasa | 朱桜 司 | すおう つかさ | suou tsukasa | ["司","tsukasa"] | 1310 | Knights | 追加 | |
| tsukinaga-reo | 月永 レオ | つきなが れお | tsukinaga reo | ["レオ","reo"] | 1320 | Knights | 追加 | |
| sena-izumi | 瀬名 泉 | せな いずみ | sena izumi | ["泉","izumi"] | 1330 | Knights | 追加 | |
| sakuma-ritsu | 朔間 凛月 | さくま りつ | sakuma ritsu | ["凛月","ritsu"] | 1340 | Knights | 追加 | UNDEADの朔間零と兄弟（朔間零が兄、朔間凛月が弟） |
| narukami-arashi | 鳴上 嵐 | なるかみ あらし | narukami arashi | ["嵐","arashi"] | 1350 | Knights | 追加 | |

#### Switch（追加ユニット）

| slug | name | name_kana | name_romaji | aliases案 | sort_order案 | unit | 状態 | 備考 |
|---|---|---|---|---|---|---|---|---|
| sakasaki-natsume | 逆先 夏目 | さかさき なつめ | sakasaki natsume | ["夏目","natsume"] | 1410 | Switch | 追加 | |
| aoba-tsumugi | 青葉 つむぎ | あおば つむぎ | aoba tsumugi | ["つむぎ","tsumugi"] | 1420 | Switch | 追加 | |
| harukawa-sora | 春川 宙 | はるかわ そら | harukawa sora | ["宙","sora"] | 1430 | Switch | 追加 | |

#### MaM（追加ユニット、単独メンバー）

| slug | name | name_kana | name_romaji | aliases案 | sort_order案 | unit | 状態 | 備考 |
|---|---|---|---|---|---|---|---|---|
| mikejima-madara | 三毛縞 斑 | みけじま まだら | mikejima madara | ["斑","madara"] | 1510 | MaM | 追加 | Double Face兼任（5章参照） |

#### Double Face（追加ユニット、新規idolなし）

このユニットは MaM の三毛縞斑 と Crazy:B の桜河こはくの組み合わせで、新しい idol レコードは不要です（5章参照）。

#### Special for Princess!（追加ユニット）

| slug | name | name_kana | name_romaji | aliases案 | sort_order案 | unit | 状態 | 備考 |
|---|---|---|---|---|---|---|---|---|
| esu | エス | えす | esu | [] | 1710 | Special for Princess! | 追加 | 漢字表記なし。ローマ字表記（esu/S）要確認 |
| kanna | カンナ | かんな | kanna | [] | 1720 | Special for Princess! | 追加 | 漢字表記なし |
| yume | ユメ | ゆめ | yume | [] | 1730 | Special for Princess! | 追加 | 漢字表記なし |
| raika | ライカ | らいか | raika | [] | 1740 | Special for Princess! | 追加 | 漢字表記なし |

このユニット4人は全体的に確認優先度が高いです（4章参照）。

### 先生

#### Jin & Akiomi（追加ユニット、教師キャラクター）

| slug | name | name_kana | name_romaji | aliases案 | sort_order案 | unit | 状態 | 備考 |
|---|---|---|---|---|---|---|---|---|
| sagami-jin | 佐賀美 陣 | さがみ じん | sagami jin | ["陣","jin"] | 1810 | Jin & Akiomi | 追加 | 教師キャラ。MV衣装対象として扱う。ただし衣装種別や実装範囲は運用上確認 |
| kunugi-akiomi | 椚 章臣 | くぬぎ あきおみ | kunugi akiomi | ["章臣","akiomi"] | 1820 | Jin & Akiomi | 追加 | 同上 |

---

## 2. unit 追加・更新差分案

事務所順・ユニット順に記載。案A（sort_order再整理）の数値です。

| slug | name | aliases案 | unit_type | member_slugs | sort_order案 | 状態 | 備考 |
|---|---|---|---|---|---|---|---|
| fine | fine | ["フィーネ"] | regular | tenshouin-eichi, hibiki-wataru, himemiya-tori, fushimi-yuzuru | 100 | 既存（sort_order変更） | 現行10→100。メンバー変更なし |
| trickstar | Trickstar | ["トリックスター"] | regular | hidaka-hokuto, akehoshi-subaru, yuuki-makoto, isara-mao | 200 | 追加 | |
| ryuuseitai | 流星隊 | [] | regular | nagumo-tetora, takamine-midori, sengoku-shinobu, morisawa-chiaki, shinkai-kanata | 300 | 追加 | slug長音表記（ryuuseitai/ryuseitai）要確認 |
| alkaloid | ALKALOID | ["アルカロイド"] | regular | amagi-hiiro, shiratori-aira, ayase-mayoi, kazehaya-tatsumi | 400 | 追加 | |
| eden | Eden | ["エデン"] | regular | ran-nagisa, tomoe-hiyori, saegusa-ibara, sazanami-jun | 500 | 追加 | |
| valkyrie | Valkyrie | ["ヴァルキリー"] | regular | itsuki-shu, kagehira-mika | 600 | 追加 | |
| 2wink | 2wink | ["とぅうぃんく"] | regular | aoi-hinata, aoi-yuuta | 700 | 追加 | 読みは「とぅうぃんく」として扱う。slugは`2wink`のまま |
| crazy-b | Crazy:B | ["クレビ","くれいじーびー"] | regular | amagi-rinne, himeru, oukawa-kohaku, shiina-niki | 800 | 追加 | 読みは「くれいじーびー」、略称は「クレビ」。slugは`crazy-b`のまま |
| undead | UNDEAD | ["アンデッド"] | regular | sakuma-rei, hakaze-kaoru, oogami-koga, otogari-adonis | 900 | 既存（sort_order変更） | 現行70→900。メンバー変更なし |
| rabits | Ra*bits | ["ラビッツ"] | regular | nito-nazuna, shino-hajime, mashiro-tomoya, tenma-mitsuru | 1000 | 既存（sort_order変更） | 現行80→1000。メンバー変更なし |
| akatsuki | 紅月 | ["あかつき"] | regular | hasumi-keito, kiryuu-kurou, kanzaki-souma, taki-ibuki | 1100 | 追加 | ユニット名の読みは あかつき / Akatsuki として扱う |
| mellow-dear-us | MELLOW DEAR US | ["メロアス","MDU"] | regular | kojika-juisu, madoka-nozomi, kuon-mashu, tsuzura-chitose | 1200 | 追加 | 「メロアス」は公式略称 |
| knights | Knights | ["ナイツ"] | regular | suou-tsukasa, tsukinaga-reo, sena-izumi, sakuma-ritsu, narukami-arashi | 1300 | 追加 | |
| switch | Switch | ["スイッチ"] | regular | sakasaki-natsume, aoba-tsumugi, harukawa-sora | 1400 | 追加 | |
| mam | MaM | [] | regular | mikejima-madara | 1500 | 追加 | 単独メンバーのユニット |
| double-face | Double Face | [] | cross（要確認） | mikejima-madara, oukawa-kohaku | 1600 | 追加 | 新規idolなし。既存2人の`member_slugs`に追記する形（5章） |
| special-for-princess | Special for Princess! | ["エスプリ","SFP"] | regular | esu, kanna, yume, raika | 1700 | 追加 | 「エスプリ」は公式略称 |
| jin-and-akiomi | Jin & Akiomi | [] | teacher | sagami-jin, kunugi-akiomi | 1800 | 追加 | 教師ユニット。MV衣装対象として扱う。ただし衣装種別や実装範囲は運用上確認 |

### 案B（最小変更）を選ぶ場合の補足

既存3ユニットの `sort_order`（fine=10, UNDEAD=70, Ra*bits=80）を変えない場合、事務所順を保ちながら詰め込むと以下のような不揃いな刻みになります（例）。

```
fine=10, Trickstar=20, 流星隊=25, ALKALOID=30, Eden=35, Valkyrie=40,
2wink=45, Crazy:B=50, UNDEAD=70, Ra*bits=80, 紅月=85, MELLOW DEAR US=90,
Knights=100, Switch=110, MaM=120, Double Face=130,
Special for Princess!=140, Jin & Akiomi=150
```

既存値は変わりませんが、刻み幅がバラバラで今後の追加余地も乏しいため、**案Aを推奨**します。

---

## 3. 既存データとの比較

### 既に登録済み（12アイドル・3ユニット）

- idols: `tenshouin-eichi` `hibiki-wataru` `himemiya-tori` `fushimi-yuzuru`（fine）／`sakuma-rei` `hakaze-kaoru` `oogami-koga` `otogari-adonis`（UNDEAD）／`nito-nazuna` `shino-hajime` `mashiro-tomoya` `tenma-mitsuru`（Ra*bits）
- units: `fine` `undead` `rabits`

これらは `slug` / `name` / `name_kana` / `name_romaji` / `aliases` / `member_slugs` を変更する必要はありません。**sort_order のみ、案A採用時に変更**が必要です（1〜2章参照）。

### 追加が必要なもの

- idols: 上記12人以外の**48人**（1章の各表の「追加」行）
- units: `fine` `undead` `rabits` 以外の**15ユニット**（Trickstar, 流星隊, ALKALOID, Eden, Valkyrie, 2wink, Crazy:B, 紅月, MELLOW DEAR US, Knights, Switch, MaM, Double Face, Special for Princess!, Jin & Akiomi）

### 既存だが member_slugs 更新が必要なもの

- なし。既存3ユニット（fine / UNDEAD / Ra*bits）の `member_slugs` は変更不要です。

### sort_order 再整理が必要そうなもの

- 既存12アイドル・3ユニットすべて（案A採用時）。詳細は1〜2章の該当行。

---

## 4. 不明点・要確認リスト

優先度が高い順に並べています。

確認済みとなった主な項目（参考）:

- **2wink のslug**: `2wink` で確定寄りとします。読みは「とぅうぃんく」（aliases追加済み）。
- **Crazy:B のslug**: `crazy-b` で確定寄りとします。読みは「くれいじーびー」、略称「クレビ」（aliases追加済み）。
- **Jin & Akiomi を含めるかどうか**: 確認済みです。先生2人にも全キャラ配布衣装の一部と元ユニット衣装があるため、今回の60キャラマスターに含めます。
- **紅月のユニット名の読み**: あかつき / Akatsuki として確定しました（slug `akatsuki`、aliases `["あかつき"]`）。
- **甘楽 チトセの読み・slug**: `tsuzura-chitose` で確定扱いとしています。

以降が、現時点で残っている不明点・要確認事項です。優先度が高い順に並べています。

1. **Special for Princess! の slug / aliases**: 4人（エス／カンナ／ユメ／ライカ）はいずれも漢字表記がなく、ローマ字表記（`esu`など）が公式表記と一致するか不明です。ユニット略称「エスプリ」は公式略称として追加済みですが、メンバー個々のローマ字表記・正式カタカナ表記は未確認です。
2. **MELLOW DEAR US の slug / aliases**: 4人の日本語カナ表記（ジュイス等）をどうローマ字化するのが公式かが不明です。特に「ジュイス」は英語の "Juice" を意図している可能性がありますが未確認です。ユニット略称「メロアス」は公式略称として追加済みです。
3. **Jin & Akiomi の衣装種別・実装範囲**: 60キャラマスターに含める方針・MV衣装対象として扱う方針は確定しましたが、実際に用意されている衣装の種別（全キャラ配布衣装／元ユニット衣装など）や実装範囲は運用上別途確認が必要です。
4. **長音を含むローマ字表記**: 以下は「u」を重ねる（yuuki）か省略する（yuki）かなど、一部公式英字表記のゆれが未確認です。
   - 遊木 真（ゆうき → yuuki/yuki）
   - 斎宮 宗（しゅう → shu/shuu）
   - 葵 ゆうた（ゆうた → yuuta/yuta）
   - 鬼龍 紅郎（きりゅう くろう → kiryuu kurou / kiryu kuro）
   - 神崎 颯馬（そうま → souma/soma）
   - 流星隊（りゅうせいたい → ryuuseitai/ryuseitai）
5. **HiMERU の aliases**: 漢字表記がないため、追加のaliasesが必要かどうか未確認です（現状は空欄で提案）。
6. **Double Face の unit_type**: 既存の値は `regular` のみです。他ユニットのメンバーを掛け合わせた「クロスユニット」的な性質を表すため `cross` という新しい値を提案していますが、命名は未確定です。
7. **MaM の aliases**: カタカナ通称が不明なため、aliases案を空欄にしています。

---

## 5. JSON反映時の最小スコープ案

次回、実際にJSONへ反映するとしたら、以下のスコープを想定しています（今回は実施していません）。

- `public/data/idols.json` に、1章の「追加」行（48人分。Jin & Akiomiの2人を含む）を追加する
- `public/data/idols.json` の既存12人分の `sort_order` を、案A採用時は更新する（slug/name等は変更なし）
- `public/data/units.json` に、2章の「追加」行（15ユニット。Jin & Akiomiを含む）を追加する
- `public/data/units.json` の既存3ユニット（fine/undead/rabits）の `sort_order` を、案A採用時は更新する（member_slugsは変更なし）
- `public/data/units.json` の `mam` の `member_slugs` には `mikejima-madara` のみ、`double-face` の `member_slugs` には `mikejima-madara` と `oukawa-kohaku` の両方を入れる（複数ユニット所属は既存方針どおり `member_slugs` 側で表現し、idol側に所属情報は持たせない）
- コード変更なし（`app.js` は `unit_type` を参照していないため、新しい値を追加しても表示ロジックの変更は不要）
- 画像変更なし
- `public/data/costumes.json` は今回のスコープ外（アイドルマスタ・ユニットマスタの追加のみ。衣装レコード自体は別途）

反映前に、4章の要確認事項（特にSpecial for Princess!・MELLOW DEAR USの英字表記、Jin & Akiomiの衣装種別・実装範囲）について回答をもらってから着手するのが安全です。
