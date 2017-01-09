<?php 

define('DB_HOST', "external-db.s4086.gridserver.com");
define('DB_NAME', "db4086_modd");
define('DB_USER', "db4086_modd_usr");
define('DB_PASS', "f4zeHUga.age");

// make the connection
$db_conn = mysqli_connect(DB_HOST, DB_USER, DB_PASS) or die("Could not connect to database\n");

// select the proper db
mysqli_select_db($db_conn, DB_NAME) or die("Could not select database\n");
mysqli_set_charset($db_conn, 'utf8');

// reset all to disabled
$query = 'UPDATE `fb_products` SET `enabled` = 0;';
$result = mysqli_query($db_conn, $query);

// select closest to date - 24h
$query = 'SELECT `id`, `name`, `price`, `image_url`, `video_url`, `added` FROM `fb_products` WHERE `added` > DATE_SUB(NOW(), INTERVAL 24 HOUR) LIMIT 1;';
$result = mysqli_query($db_conn, $query);
$product_obj = mysqli_fetch_object($result);
mysqli_free_result($result);

// make it enabled
$query = 'UPDATE `fb_products` SET `enabled` = 1 WHERE `id` = '. $product_obj->id .';';
$result = mysqli_query($db_conn, $query);

$date1 = new DateTime($product_obj->added);
$date2 = new DateTime("now");
$interval = $date1->diff($date2);

// $query = 'SELECT DISTINCT `chat_id` FROM `fbbot_logs`;';
$query = 'SELECT DISTINCT `chat_id` FROM `fbbot_logs` WHERE `chat_id` = "1219553058088713" LIMIT 1;';
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
	curl_setopt($ch, CURLOPT_URL, "https://graph.facebook.com/v2.6/me/messages?access_token=EAAXFDiMELKsBAM0ukSiFZBhCHFWJIqMHhv1uwuL0GZB59PZC7AljrESQetUJRlusUTkzyMnM67Ahn9etkboS4ZCXIRoipiIUIYUh11nx3FQqDRKLxdGZCWSsONZBwQEpjV67GV7majCwB5iTUaaDPoQZC3FAIAxZCeQ5cdqhE9DSMBKS9Gzpv9Yt");
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
	  'message'             => array(
		  'attachment' => array(
			  'type'    => "template",
		    'payload' => array(
			    'template_type' => "generic",
		      'elements'      => array(
			      array(
              'title'      => $product_obj->name ." went on sale for $". $product_obj->price,
			         'subtitle'  => "",
			         'image_url' => "",
			         'item_url'  => "https://prebot.chat/stripe.php?from_user=". $user_obj->chat_id ."&item_id=". $product_obj->id,
			         'buttons'   => array(
				        array(
					        'type'  => "web_url",
                  'url'   => "https://prebot.chat/stripe.php?from_user=". $user_obj->chat_id ."&item_id=". $product_obj->id,
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
	curl_setopt($ch, CURLOPT_URL, "https://graph.facebook.com/v2.6/me/messages?access_token=EAAXFDiMELKsBAM0ukSiFZBhCHFWJIqMHhv1uwuL0GZB59PZC7AljrESQetUJRlusUTkzyMnM67Ahn9etkboS4ZCXIRoipiIUIYUh11nx3FQqDRKLxdGZCWSsONZBwQEpjV67GV7majCwB5iTUaaDPoQZC3FAIAxZCeQ5cdqhE9DSMBKS9Gzpv9Yt");
	curl_setopt($ch, CURLOPT_POST, 1);
	curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload_arr));
	curl_setopt($ch, CURLOPT_HTTPHEADER, array("Content-Type: application/json"));
	curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
	curl_setopt($ch, CURLOPT_FAILONERROR, 1);
	curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 300);
	curl_setopt($ch, CURLOPT_TIMEOUT, 60);

	$res = json_decode(curl_exec($ch), true);
	curl_close($ch);
}

mysqli_free_result($result);
?>
