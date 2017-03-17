<?php 

define('DB_HOST', "external-db.s4086.gridserver.com");
define('DB_NAME', "db4086_modd");
define('DB_USER', "db4086_modd_usr");
define('DB_PASS', "f4zeHUga.age");

define('BROADCASTER_ADDR', "162.243.150.21");
define('BROADCASTER_USER_AGENT', "GameBots-Broadcaster-v3");
define('FB_MESSAGE_TEMPLATE_PATH', "/opt/cron/etc/". basename(__FILE__, ".php") .".conf");


function send_tracker($fb_psid) {
  $tracking_arr = array(
    array(
      'category' => "broadcast",
      'action'   => "broadcast",
      'label'    => $fb_psid,
      'value'    => 0,
      'cid'      => md5(BROADCASTER_ADDR)
    ),
    array(
      'category' => "user-message",
      'action'   => "user-message",
      'label'    => $fb_psid,
      'value'    => 0,
      'cid'      => md5(BROADCASTER_ADDR)
    )
  );
  
  $response_arr = array();
  foreach ($tracking_arr as $val) {
    $ch = curl_init();
    curl_setopt_array($ch, array(
    	CURLOPT_USERAGENT      => BROADCASTER_USER_AGENT,
    	CURLOPT_RETURNTRANSFER => true,
    	CURLOPT_URL            => sprintf("http://beta.modd.live/api/bot_tracker.php?src=facebook&category=%s&action=%s&label=%s&value=%d&cid=%s", $val['category'], $val['action'], $val['label'], $val['value'], $val['cid'])
    ));
    
    array_push($response_arr, curl_exec($ch));
    curl_close($ch);
  }
}

function post_message($url, $payload_obj) {
  $ch = curl_init();
	curl_setopt($ch, CURLOPT_URL, $url);
	curl_setopt($ch, CURLOPT_POST, 1);
	curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload_obj));
	curl_setopt($ch, CURLOPT_HTTPHEADER, array("Content-Type: application/json"));
	curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
	curl_setopt($ch, CURLOPT_FAILONERROR, 1);
	curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 300);
	curl_setopt($ch, CURLOPT_TIMEOUT, 60);

	$response = curl_exec($ch);
	curl_close($ch);
	
	if (strlen($response) > 0) {
	  echo($response ."\n");
	}
}


// make the connection
$db_conn = mysqli_connect(DB_HOST, DB_USER, DB_PASS) or die("Could not connect to database\n");

// select the proper db
mysqli_select_db($db_conn, DB_NAME) or die("Could not select database\n");
mysqli_set_charset($db_conn, 'utf8');

// open txt config for templates
$config_arr = array(
  'FB_GRAPH_API'        => "https://graph.facebook.com/v2.6/me/messages",
  'FB_ACCESS_TOKEN'     => "EAAXFDiMELKsBAESoNb9hvGcOarJZCSuHJOQCjC835GS1QwwlOn8D255xPF86We1Wxg4DtxQqr91aHFYjFoOybUOVBTdtDalFKNLcjA2EXTEIGHXEMRbsA4vghEWKiIpB6nbzsX6G5rYBZCHuBc1UlsUnOqwZAS2jY56xppiIgZDZD",
  'BODY_TEMPLATE'       => "Items are re-loaded! come flip."
);

$handle = @fopen(FB_MESSAGE_TEMPLATE_PATH, 'r');
if ($handle) {
  
  // read in the line
  while (($buffer = fgets($handle, 4096)) !== false) {
    if (preg_match('/^[#$]/i', $buffer) || preg_match('/^\s*$/i', $buffer)) {
      continue;
    
    } else {
      preg_match('/^(?P<key>[A-Z_]+)\t(?P<val>.*)$/', $buffer, $match_arr);
      if (array_key_exists('key', $match_arr) && array_key_exists('val', $match_arr)) {
        $config_arr[$match_arr['key']] = $match_arr['val'];
      }
    }
  }

  // eof error
  if (!feof($handle)) {
    //$message_template = FB_ORTHODOX_MESSAGE_TEMPLATE;
  }
  
  fclose($handle);

} else {
  echo("Couldn't open config file! ". FB_MESSAGE_TEMPLATE_PATH ."\n");
}

$body_txt = $config_arr['BODY_TEMPLATE'];


// get list of recipients
$query = (count($argv) == 2) ? 'SELECT DISTINCT `chat_id` FROM `fbbot_logs` WHERE `chat_id` = "'. $argv[1] .'" LIMIT 1;' : 'SELECT DISTINCT `chat_id` FROM `fbbot_logs` WHERE `enabled` = 1;';
$result = mysqli_query($db_conn, $query);

// summary
echo("Sending to ". number_format(mysqli_num_rows($result)) ." total users w/ message: \"". $body_txt ."\"\n[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]\n");

// iterate
$cnt = 0;
while ($user_obj = mysqli_fetch_object($result)) {
  
  // output status
  echo(sprintf("FB (%05s/%05s)--> [%-16s]\n", number_format(++$cnt), number_format(mysqli_num_rows($result)), $user_obj->chat_id));
  
  // build json array
  $payload_arr = array(
    'recipient' => array(
      'id' => $user_obj->chat_id
    ),
    'message' => array(
      'text' => $body_txt,
      'quick_replies' => array(
        array(
          'content_type' => "text",
          'title'        => "Main Menu",
          'payload'      => "MAIN_MENU"
        )
      )
    )
  );

  post_message($config_arr['FB_GRAPH_API'] ."?access_token=". $config_arr['FB_ACCESS_TOKEN'], $payload_arr);
  send_tracker($user_obj->chat_id);
}

mysqli_free_result($result);

// close db
if ($db_conn) {
	mysqli_close($db_conn);
	$db_conn = null;
}

?>
