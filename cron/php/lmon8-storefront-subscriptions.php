<?php

define('DB_HOST', "138.197.216.56");
define('DB_NAME', "prebot_marketplace");
define('DB_USER', "pre_usr");
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
    	CURLOPT_URL            => sprintf("http://beta.modd.live/api/bot_tracker.php?src=prebot&category=%s&action=%s&label=%s&value=%d&cid=%s", $val['category'], $val['action'], $val['label'], $val['value'], $val['cid'])
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
  'FB_GRAPH_API'    => "https://graph.facebook.com/v2.6/me/messages",
  'FB_ACCESS_TOKEN' => "EAADzAMIzYPEBAJGk5P18ibMeEBhhdvUzZBsMoItnuB19PEzUGnNZALX5MN1rK0HKEfSG4YsmyVM2NmeK3m9wcmDvmwoB97aqfn1U0KOdvNtv6ZCgPLvqPFr2YbnlinuUUSrPtnphqafj6ad73wIPVBCOhCaiLGfvEZCUr7CxcAZDZD",
  'BODY_TEMPLATE'   => "\"%s\" has %d new subscriber%s in the last 24 hours.\n"
);

$handle = @fopen(FB_MESSAGE_TEMPLATE_PATH, 'r');
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
  echo("Couldn't open config file! ". FB_MESSAGE_TEMPLATE_PATH ."\n");
}


// fetch storefronts
$query = (count($argv) == 2) ? 'SELECT `storefronts`.`id`, `users`.`fb_psid`, `storefronts`.`display_name` FROM `users` INNER JOIN `storefronts` ON `users`.`id` = `storefronts`.`owner_id` WHERE `users`.`fb_psid` = '. $argv[1] .' LIMIT 1;' : 'SELECT `storefronts`.`id`, `users`.`fb_psid`, `storefronts`.`display_name` FROM `users` INNER JOIN `storefronts` ON `users`.`id` = `storefronts`.`owner_id` WHERE `storefronts`.`enabled` = 1 AND `storefronts`.`type` != 0;';
$result = mysqli_query($db_conn, $query);

// has active stores
$storefronts_arr = array();
while ($storefront_obj = mysqli_fetch_object($result)) {
	$query = 'SELECT COUNT(*) AS `cnt` FROM `subscriptions` WHERE `storefront_id` = '. $storefront_obj->id .' AND `added` > DATE_SUB(NOW(), INTERVAL 24 HOUR) GROUP BY `storefront_id`;';
	$sub_result = mysqli_query($db_conn, $query);
	
	$storefronts_arr[$storefront_obj->fb_psid] = array(
	  'display_name' => $storefront_obj->display_name,
	  'total'        => (mysqli_num_rows($sub_result) > 0) ? mysqli_fetch_object($sub_result)->cnt : 0
	);
}

mysqli_free_result($result);


// close db
if ($db_conn) {
	mysqli_close($db_conn);
	$db_conn = null;
}

$cnt = 0;
foreach ($storefronts_arr as $key=>$val) {

  // output status
  echo(sprintf("FB (%05s/%05s)--> [%-16s]\n", number_format(++$cnt), number_format(count($storefronts_arr)), $key));
  
  // build json array
  $payload_arr = array(
    'recipient' => array(
			'id' => $key
		),
		'message'   => array(
		  'attachment' => array(
		    'type'    => "image",
		    'payload' => array(
		      'url' => "https://i.imgur.com/73iVUkb.gif"
		    )
		  )
		)
  );
  post_message($config_arr['FB_GRAPH_API'] ."?access_token=". $config_arr['FB_ACCESS_TOKEN'], $payload_arr);
  
    
  // build json array
  $payload_arr = array(
		'recipient' => array(
			'id' => $key
		),
		'message'   => array(
		  'text'          => sprintf($config_arr['BODY_TEMPLATE'], $val['display_name'], $val['total'], ($val['total'] == 1) ? "" : "s"),
		  'quick_replies' => array(
        array(
          'content_type' => "text",
          'title'        => "Menu",
          'payload'      => "MAIN_MENU"
        )
      )
    )
	);

	post_message($config_arr['FB_GRAPH_API'] ."?access_token=". $config_arr['FB_ACCESS_TOKEN'], $payload_arr);
  send_tracker($key);
}

?>