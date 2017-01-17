<?php

define('DB_HOST', "138.197.216.56");
define('DB_NAME', "prebot_marketplace");
define('DB_USER', "pre_usr");
define('DB_PASS', "f4zeHUga.age");

define('BROADCASTER_ADDR', "162.243.150.21");
define('BROADCASTER_USER_AGENT', "GameBots-Broadcaster-v3");
define('FB_MESSAGE_TEMPLATE_PATH', "/opt/cron/etc/fb-owner-notify.conf");
define('FB_GRAPH_API', "https://graph.facebook.com/v2.6/me/messages?access_token=EAAXFDiMELKsBAM0ukSiFZBhCHFWJIqMHhv1uwuL0GZB59PZC7AljrESQetUJRlusUTkzyMnM67Ahn9etkboS4ZCXIRoipiIUIYUh11nx3FQqDRKLxdGZCWSsONZBwQEpjV67GV7majCwB5iTUaaDPoQZC3FAIAxZCeQ5cdqhE9DSMBKS9Gzpv9Yt");

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
			CURLOPT_URL            => sprintf("http://beta.modd.live/api/bot_tracker.php?src=facebook&category=%s&action=%s&label=%s&value=%d&cid=%s", $val->category, $val->action, $val->label, $val->value, $val->cid)
	));

		array_push($response_arr, json_encode(curl_exec($ch)));
		curl_close($ch);
	}

  echo(json_decode($response_arr) ."\n");
}

function post_message($payload_obj) {
	$ch = curl_init();
	curl_setopt($ch, CURLOPT_URL, FB_GRAPH_API);
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


function purddy_print($arr) {
	echo ("<pre>". print_r($arr, 1) ."</pre>\n");
}

// make the connection
$db_conn = mysqli_connect(DB_HOST, DB_USER, DB_PASS) or die("Could not connect to database\n");

// select the proper db
mysqli_select_db($db_conn, DB_NAME) or die("Could not select database\n");
mysqli_set_charset($db_conn, 'utf8');


// fetch storefronts
$query = 'SELECT `id`, `name`, `display_name`, `logo_url`, `prebot_url`, `views` FROM `storefronts` WHERE `enabled` = 1 ORDER BY `added` DESC;';
$sf_result = mysqli_query($db_conn, $query);

purddy_print(array(
	'count' => mysqli_num_rows($sf_result),
	'query' => $query
));

// has active stores
$storefronts_arr = array();
while ($storefront_obj = mysqli_fetch_object($sf_result)) {
	echo("STOREFRONT: ". purddy_print($storefront_obj));

	// prepop the storefront
	$sf_arr = array(
		'products'      => array(),
		'subscriptions' => array()
	);

	// loop thru each field
	foreach ($storefront_obj as $key => $val) {
		$sf_arr[$key] = $val;
	}

	// get this store's product(s)
	$query = 'SELECT `id`, `name`, `display_name`, `image_url`, `video_url`, `prebot_url` FROM `products` WHERE `storefront_id` = ' . $storefront_obj->id . ' AND `enabled` = 1 ORDER BY `added` DESC;';
	$prod_result = mysqli_query($db_conn, $query);

	purddy_print(array(
		'count' => mysqli_num_rows($prod_result),
		'query' => $query
	));

	// has products
	while ($product_obj = mysqli_fetch_object($prod_result)) {
		// loop thru each product
		$prods_arr = array();
		foreach ($product_obj as $key => $val) {
			$prods_arr[$key] = $val;
		}

		// append prod obj onto this store
		array_push($sf_arr, array(
			'products' => $prods_arr
		));
	}


	// list of product ids
	$prodIDs_arr = array();
	foreach ($sf_arr['products'] as $product_obj) {
		array_push($prodIDs_arr, $product_obj->id);
	}

	// get this store's / product's subscribers
	$query = 'SELECT `id`, `user_id`, `added` FROM `subscriptions` WHERE (`storefront_id` = '. $storefront_obj->id .' OR `product_id` IN ('. implode(",", $prodIDs_arr) .')) AND `enabled` = 1 ORDER BY `added` DESC;';
	$sub_result = mysqli_query($db_conn, $query);

	// has subscribers
	$subs_arr = array();
	while ($subscription_obj = mysqli_fetch_object($sub_result)) {

		// loop thru each sub
		foreach ($subscription_obj as $key => $val) {
			$subs_arr[$key] = $val;
		}

		// append subs obj onto this store
		array_push($sf_arr, array(
			'subscriptions' => $subs_arr
		));
	}

	// append store onto main
	array_push($storefronts_arr, $sf_arr);
}

print(json_encode($storefronts_arr));



// close db
if ($db_conn) {
	mysqli_close($db_conn);
	$db_conn = null;
}

?>


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
					'title'        => "Main Menu",
					'payload'      => "MAIN_MENU"
				)
			)
		)
	);
?>
