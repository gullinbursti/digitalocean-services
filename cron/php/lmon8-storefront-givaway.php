<?php

define('DB_HOST', "138.197.216.56");
define('DB_NAME', "prebot_marketplace");
define('DB_USER', "pre_usr");
define('DB_PASS', "f4zeHUga.age");


// make the connection
$db_conn = mysqli_connect(DB_HOST, DB_USER, DB_PASS) or die("Could not connect to database\n");

// select the proper db
mysqli_select_db($db_conn, DB_NAME) or die("Could not select database\n");
mysqli_set_charset($db_conn, 'utf8');


// fetch subscribers
$query = 'SELECT `fb_psid` FROM `users` WHERE `id` IN (SELECT DISTINCT(`user_id`) FROM `subscriptions` WHERE `enabled` = 1 AND `storefront_id` IN (SELECT `id` FROM `storefronts` WHERE `giveaway` = 1))';
$result = mysqli_query($db_conn, $query);

// sending report
echo("Sending to ". number_format(mysqli_num_rows($result)) ." total users\n[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]\n");

// loop thru fb ids
$cnt = 0;
while ($user_obj = mysqli_fetch_object($result)) {  
  
  // current iteration
  echo(sprintf("SENDING --> (%05s/%05s)--> [%-16s]\n", number_format(++$cnt), number_format(mysqli_num_rows($result)), $user_obj->fb_psid));
  
  // send to api
  $ch = curl_init();
	curl_setopt($ch, CURLOPT_URL, "http://beta.modd.live/api/coin_flip.php?token=". time());
	curl_setopt($ch, CURLOPT_POST, 1);
	curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query(array(
	 'action'    => "NEXT_ITEM",
	 'social_id' => $user_obj->fb_psid
	)));
	curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
	curl_setopt($ch, CURLOPT_FAILONERROR, 1);
	curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 300);
	curl_setopt($ch, CURLOPT_TIMEOUT, 60);

	$response = curl_exec($ch);
	curl_close($ch);
}


// close db
if ($db_conn) {
	mysqli_close($db_conn);
	$db_conn = null;
}

?>