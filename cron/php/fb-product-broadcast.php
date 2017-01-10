<?php 

define('DB_HOST', "external-db.s4086.gridserver.com");
define('DB_NAME', "db4086_modd");
define('DB_USER', "db4086_modd_usr");
define('DB_PASS', "f4zeHUga.age");

define('BROADCASTER_ADDR', "162.243.150.21");
define('FB_GRAPH_API', "https://graph.facebook.com/v2.6/me/messages?access_token=EAAXFDiMELKsBAM0ukSiFZBhCHFWJIqMHhv1uwuL0GZB59PZC7AljrESQetUJRlusUTkzyMnM67Ahn9etkboS4ZCXIRoipiIUIYUh11nx3FQqDRKLxdGZCWSsONZBwQEpjV67GV7majCwB5iTUaaDPoQZC3FAIAxZCeQ5cdqhE9DSMBKS9Gzpv9Yt");


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

$query = 'SELECT DISTINCT `chat_id` FROM `fbbot_logs`;';
//$query = 'SELECT DISTINCT `chat_id` FROM `fbbot_logs` WHERE `chat_id` = "1219553058088713" LIMIT 1;';
$result = mysqli_query($db_conn, $query);

while ($user_obj = mysqli_fetch_object($result)) {
  echo ("FB --> ". $user_obj->chat_id ."\n");
  $payload_arr = array(
		'recipient' => array(
			'id' => $user_obj->chat_id
		),
		'message'   => array(
			'attachment' => array(
				'type'    => "image",
				'payload' => array(
					'url' => $product_obj->video_url
				)
			),
			'quick_replies' => array(
				array(
					'content_type' => "text",
					'title'        => "Main Menu",
					'payload'      => "MAIN_MENU"
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

	$res = json_decode(curl_exec($ch), true);
	curl_close($ch);

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
              'title'      => $product_obj->name ." went on sale for $". $product_obj->price,
			         'subtitle'  => "",
			         'image_url' => "",
			         'item_url'  => "http://prekey.co/stripe/". $product_obj->id ."/". $user_obj->chat_id,
			         'buttons'   => array(
				        array(
					        'type'  => "web_url",
                  'url'   => "http://prekey.co/stripe/". $product_obj->id ."/". $user_obj->chat_id,
                  'title' => "Buy"
				        )
			        )
			      )
		      )
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

	$res = json_decode(curl_exec($ch), true);
	curl_close($ch);
	
	
  $ch = curl_init();
  curl_setopt_array($ch, array(
  	CURLOPT_USERAGENT => "GameBots-Tracker-v2",
  	CURLOPT_RETURNTRANSFER => true,
  	CURLOPT_URL => "http://beta.modd.live/api/bot_tracker.php?src=facebook&category=broadcast&action=broadcast&label=". $user_obj->chat_id ."&value=&cid=". md5(BROADCASTER_ADDR)
  ));

  $res = curl_exec($ch);
  curl_close($ch);
  
  $ch = curl_init();
  curl_setopt_array($ch, array(
  	CURLOPT_USERAGENT => "GameBots-Tracker-v2",
  	CURLOPT_RETURNTRANSFER => true,
  	CURLOPT_URL => "http://beta.modd.live/api/bot_tracker.php?src=facebook&category=user-message&action=user-message&label=". $user_obj->chat_id ."&value=&cid=". md5(BROADCASTER_ADDR)
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
