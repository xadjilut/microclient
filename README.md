# microclient /ArmyRF :ru:
<img src="https://github.com/xadjilut/microclient/blob/master/microclient_logo.jpg?raw=true" width="50%" height="30%"/>
<br>
Unofficial Telegram client for all devices, e.g. push-button phones.
<br>
Alternative <a href="https://github.com/D4n13l3k00/tapkofon">project</a> from another author.
<h2>Features</h2>
This full client web-app allow to receive text messages, images, stickers and voice messages, send text and voice messages. Also microclient support opening internet-sites for gathering text content without media, styles and scripts.
<h2>Requirements</h2>
<ul>
  <li>FFmpeg <i>(for voice convert)</i></li>
  <li>Python 3.6+</li>
</ul>

<h2>Installation</h2>
<h3>Manual:</h3>
<code>python3 -m pip install --user -r requirements.txt</code>

<h2>Configuration</h2>
<ul>
  <li><p>Obtain api credentials (<code>api_id</code> and <code>api_hash</code>) to https://my.telegram.org</p></li>
  <li><p>For enable a guest mode, you can found session file with "session" name using terminal:</p>
    <p><code>python microclient.py --api-id &#60;your api_id&#62; --api-hash &#60;your api_hash&#62; --setup-guest</code></p>
  <p>Enter phone, code, optional password and close terminal.</p></li>
</ul>

<h2>Running</h2>
<code>python3 microclient.py</code>

<h2>Visualization</h2>
<p>Open <code>http://localhost:8090/armyrf</code> in your horny browser (or cURL, wget, python requests, lol) and funny.</p>
<h4>Listed routes:</h4>
<ul>
  <li>/armyrf</li>
  <li>/armyrf/&lt;xid&gt;</li>
  <li>/armyrf/auth</li>
  <li>/armyrf/dl</li>
  <li>/armyrf/dl/&lt;filename&gt;</li>
  <li>/armyrf/faq</li>
  <li>/armyrf/logout</li>
  <li>/armyrf/pass</li>
  <li>/armyrf/profile</li>
  <li>/armyrf/reply</li>
  <li>/armyrf/search</li>
  <li>/armyrf/search/&lt;entity_str&gt;</li>
  <li>/armyrf/wat</li>
  <li>/microlog/&lt;secret_part&gt;</li>
  <li>/p</li>
  <li>/time</li>
  <li>/ua</li>
</ul>

<h2>Docker</h2>
<h3>Build:</h3><code>docker build -t microclient .</code>
<h3>Run it:</h3>
<code>docker run -d -p 8090:8090 -v $(pwd):/root microclient</code>

<h1>❗️Deploy it before the start of general mobilization!🚀</h1>
