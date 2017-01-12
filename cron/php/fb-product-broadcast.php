<?php 

define('DB_HOST', "external-db.s4086.gridserver.com");
define('DB_NAME', "db4086_modd");
define('DB_USER', "db4086_modd_usr");
define('DB_PASS', "f4zeHUga.age");

define('BROADCASTER_ADDR', "162.243.150.21");
define('BROADCASTER_USER_AGENT', "GameBots-Broadcaster-v3");
define('FB_ORTHODOX_MESSAGE_TEMPLATE', "_{PRODUCT_NAME}_ went on sale for \$_{PRICE}_.");
define('FB_MESSAGE_TEMPLATE_PATH', "/opt/cron/etc/fb-product-broadcast.conf");
define('FB_GRAPH_API', "https://graph.facebook.com/v2.6/me/messages?access_token=EAAXFDiMELKsBAM0ukSiFZBhCHFWJIqMHhv1uwuL0GZB59PZC7AljrESQetUJRlusUTkzyMnM67Ahn9etkboS4ZCXIRoipiIUIYUh11nx3FQqDRKLxdGZCWSsONZBwQEpjV67GV7majCwB5iTUaaDPoQZC3FAIAxZCeQ5cdqhE9DSMBKS9Gzpv9Yt");
define('STRIPE_URL_TEMPLATE', 'http://prekey.co/stripe/_{PRODUCT_ID}_/_{TO_USER}_');

// make the connection
$db_conn = mysqli_connect(DB_HOST, DB_USER, DB_PASS) or die("Could not connect to database\n");

// select the proper db
mysqli_select_db($db_conn, DB_NAME) or die("Could not select database\n");
mysqli_set_charset($db_conn, 'utf8');

// select closest to date - 24h
$query = 'SELECT `id`, `name`, `price`, `image_url`, `video_url`, `added` FROM `fb_products` WHERE `enabled` = 1 LIMIT 1;';
$result = mysqli_query($db_conn, $query);

// nothing found
if (mysqli_num_rows($result) == 0) {
  mysqli_free_result($result);
  exit();
}

$product_obj = mysqli_fetch_object($result);
mysqli_free_result($result);

$date1 = new DateTime($product_obj->added);
$date2 = new DateTime("now");
$interval = $date1->diff($date2);

// open txt 1-liner for template
$message_template = FB_ORTHODOX_MESSAGE_TEMPLATE;
$handle = @fopen(FB_MESSAGE_TEMPLATE_PATH, 'r');
if ($handle) {
  
  // read in the line
  while (($buffer = fgets($handle, 4096)) !== false) {
    if (preg_match('/^#(.*)/i', $buffer)) {
      continue;
    
    } else {
      $message_template = $buffer;
    }
  }

  // eof error
  if (!feof($handle)) {
    $message_template = FB_ORTHODOX_MESSAGE_TEMPLATE;
  }

  fclose($handle);

} else {
  echo("Couldn't open template file, using default: ". FB_ORTHODOX_MESSAGE_TEMPLATE);
}


// replace template tokens w/ content
$body_txt = preg_replace('/_\{PRODUCT_NAME\}_/', $product_obj->name, $message_template);
$body_txt = preg_replace('/_\{PRICE\}_/', $product_obj->price, $body_txt);
$body_txt = preg_replace('/_\{HOURS\}_/', $interval->h, $body_txt);
$body_txt = preg_replace('/_\{MINUTES\}_/', $interval->m, $body_txt);
$body_txt = preg_replace('/_\{SECONDS\}_/', $interval->s, $body_txt);
$stripe_url = preg_replace('/_\{PRODUCT_ID\}_/', $product_obj->id, STRIPE_URL_TEMPLATE);


$query = (count($argv) == 2) ? 'SELECT DISTINCT `chat_id` FROM `fbbot_logs` WHERE `chat_id` = "'. $argv[1] .'" LIMIT 1;' : 'SELECT DISTINCT `chat_id` FROM `fbbot_logs`;';
$result = mysqli_query($db_conn, $query);

echo("Sending to ". number_format(mysqli_num_rows($result)) ." total users w/ message: \"". $body_txt ."\" & card image: [". $product_obj->image_url ."]\n");

$cnt = 0;
while ($user_obj = mysqli_fetch_object($result)) {
  
  // output status
  echo(sprintf("FB (%05s/%05s)--> [%-16s]\n", number_format(++$cnt), number_format(mysqli_num_rows($result)), $user_obj->chat_id));
  
  $payload_arr = array(
		'recipient' => array(
			'id'      => $user_obj->chat_id
		),
	  'message' => array(
		  'attachment' => array(
			  'type'    => "template",
		    'payload' => array(
			    'template_type' => "generic",
		      'elements'      => array(
			      array(
              'title'      => $body_txt,
			         'subtitle'  => "",
			         'image_url' => $product_obj->image_url,
			         'item_url'  => preg_replace('/_\{TO_USER\}_/', $user_obj->chat_id, $stripe_url),
			         'buttons'   => array(
 				        array(
 					        'type'   => "web_url",
                   'url'   => preg_replace('/_\{TO_USER\}_/', $user_obj->chat_id, $stripe_url),
                   'title' => "Buy"
 				        )
               )
			      )
		      )
		    )
		  ),
		  'quick_replies' => array(
        array(
          'content_type' => "text",
          'title' => "Main Menu",
          'payload' => "MAIN_MENU"
        )
      )
	  )
	);

	$ch = curl_init();
	curl_setopt($ch, CURLOPT_URL, FB_GRAPH_API);
	curl_setopt($ch, CURLOPT_POST, 1);
	curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload_arr));
	curl_setopt($ch, CURLOPT_HTTPHEADER, array("Content-Type: application/json"));
	curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
	curl_setopt($ch, CURLOPT_FAILONERROR, 1);
	curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 300);
	curl_setopt($ch, CURLOPT_TIMEOUT, 60);

	$res = curl_exec($ch);
	curl_close($ch);
	
	if (strlen($res) > 0) {
	  echo ("RESULT: ". $res ."\n");  
	}
	
	
  $ch = curl_init();
  curl_setopt_array($ch, array(
  	CURLOPT_USERAGENT      => BROADCASTER_USER_AGENT,
  	CURLOPT_RETURNTRANSFER => true,
  	CURLOPT_URL            => "http://beta.modd.live/api/bot_tracker.php?src=facebook&category=broadcast&action=broadcast&label=". $user_obj->chat_id ."&value=&cid=". md5(BROADCASTER_ADDR)
  ));

  $res = curl_exec($ch);
  curl_close($ch);
  
  $ch = curl_init();
  curl_setopt_array($ch, array(
  	CURLOPT_USERAGENT      => BROADCASTER_USER_AGENT,
  	CURLOPT_RETURNTRANSFER => true,
  	CURLOPT_URL            => "http://beta.modd.live/api/bot_tracker.php?src=facebook&category=user-message&action=user-message&label=". $user_obj->chat_id ."&value=&cid=". md5(BROADCASTER_ADDR)
  ));

  $res = curl_exec($ch);
  curl_close($ch);
  
}

mysqli_free_result($result);

// close db
if ($db_conn) {
	mysqli_close($db_conn);
	$db_conn = null;
}

?>
