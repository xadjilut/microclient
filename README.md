# microclient /ArmyRF :ru:
Unofficial Telegram client for all devices, e.g. push-button phones.
<br>
<h2>Features</h2>
This app allow to read text messages, images, stickers and voice messages. Also microclient support opening internet-sites for gathering text content without media, styles and scripts.
<h2>Requirements</h2>
<ul>
  <li>FFmpeg <i>(for voice convert)</i></li>
  <li>Python 3.6+</li>
</ul>

<h2>Installation</h2>
<code>python3 -m pip install --user -r requirements.txt</code>

<h2>Configuration</h2>
<ul>
  <li>Obtain api credentials (<code>api_id</code> and <code>api_hash</code>) to https://my.telegram.org and put it in values.py</li>
  <li>Found session file with "session" name using Telethon</li>
  <li><p>Change <code>aeskey</code> in values.py before deploying in public server
</ul>

<h2>Running</h2>
<code>python3 microclient.py</code>

<h2>Visualization</h2>
<p>Open <code>http://localhost:8090/armyrf</code> in your horny browser (or cURL, wget, python requests, lol) and funny.</p>
<h4>Listed routes:</h4>
<ul>
  <li>/armyrf</li>
  <li>/armyrf/wat</li>
  <li>/armyrf</li>
  <li>/armyrf/&lt;entity_id&gt;</li>
  <li>/armyrf/dl</li>
  <li>/armyrf/dl/&lt;filename&gt;</li>
  <li>/armyrf/reply</li>
  <li>/armyrf/search</li>
  <li>/armyrf/search/&lt;entity_str&gt;</li>
  <li>/p</li>
  <li>/ua</li>
  <li>/time</li>
</ul>
<br>
<b>Good luck!<b>
