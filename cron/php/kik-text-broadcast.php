<?php 

define('DB_HOST', "external-db.s4086.gridserver.com");
define('DB_NAME', "db4086_modd");
define('DB_USER', "db4086_modd_usr");
define('DB_PASS', "f4zeHUga.age");

// bot info
define('BROADCASTER_ADDR', "162.243.150.21");
define('BROADCASTER_USER_AGENT', "GameBots-Broadcaster-v3");
define('KIKBOT_MESSAGE_TEMPLATE_PATH', "/opt/cron/etc/kik-text-broadcast.conf");

// make the connection
$db_conn = mysqli_connect(DB_HOST, DB_USER, DB_PASS) or die("Could not connect to database\n");

// select the proper db
mysqli_select_db($db_conn, DB_NAME) or die("Could not select database\n");
mysqli_set_charset($db_conn, 'utf8');

// open txt config for templates
$config_arr = array(
  'KIKBOT_HOST'            => "http://159.203.250.4:8080",
  'KIKBOT_WEBHOOK'         => "/message",
  'KIKBOT_BROADCAST_TOKEN' => "f7d3612391b5ba4d89d861bea6283726",
  'BODY_TEMPLATE'          => "Want a chance to win a Frontside Misty? Get Gamebots on m.me/gamebotsc"
);


// open txt 1-liner for template
$handle = @fopen(KIKBOT_MESSAGE_TEMPLATE_PATH, 'r');
if ($handle) {
  
  // read in the line
  while (($buffer = fgets($handle, 4096)) !== false) {
    if (preg_match('/^[#$]/i', $buffer) || preg_match('/^\s*$/i', $buffer)) {
      continue;
    
    } else {
      preg_match('/^(?P<key>[A-Z_]+)\t(?P<val>.*)$/', $buffer, $match_arr);
      $config_arr[$match_arr['key']] = $match_arr['val'];
    }
  }

  // eof error
  if (!feof($handle)) {
    //$message_template = FB_ORTHODOX_MESSAGE_TEMPLATE;
  }
  
  fclose($handle);
  
} else {
  echo("Couldn't open config file! ". KIKBOT_MESSAGE_TEMPLATE_PATH ."\n");
}

$body_txt = $config_arr['BODY_TEMPLATE'];


// use defined name as argv 'php kik-product-broadcast.php "btzDoh"'
$query = (count($argv) == 2) ? 'SELECT `username`, `chat_id` FROM `kikbot_logs` WHERE `username` = "'. $argv[1] .'" ORDER BY `added` DESC LIMIT 1;' : 'SELECT DISTINCT(`username`), `chat_id` FROM `kikbot_logs` WHERE `active` = 1 ORDER BY `added` DESC;';
$result = mysqli_query($db_conn, $query);

echo("Sending to ". number_format(mysqli_num_rows($result)) ." total users w/ message: \"". $body_txt ."\"\n[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]\n");

// iterate
$cnt = 0;
while ($user_obj = mysqli_fetch_object($result)) {

  // output status
  echo(sprintf("KIK ([%05s]/[%05s])--> [%-64s] \"%s\"\n", number_format(++$cnt), number_format(mysqli_num_rows($result)), $user_obj->chat_id, $user_obj->username));

  // curl off to webhook
  $curl = curl_init();
  curl_setopt_array($curl, array(
    CURLOPT_USERAGENT => BROADCASTER_USER_AGENT,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_POST => 1,
    CURLOPT_POSTFIELDS => http_build_query(array(
      'token' => $config_arr['KIKBOT_BROADCAST_TOKEN'],
      'to_user' => $user_obj->username,
      'chat_id' => $user_obj->chat_id,
      'message' => $body_txt
    )),
    CURLOPT_URL => $config_arr['KIKBOT_HOST'] . $config_arr['KIKBOT_WEBHOOK']
  ));

  $r = curl_exec($curl);
  curl_close($curl);
}

mysqli_free_result($result);

// close db
if ($db_conn) {
	mysqli_close($db_conn);
	$db_conn = null;
}

?>