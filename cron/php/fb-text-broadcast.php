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

// text content file
$message_body = "";
$handle = @fopen("/opt/modd/txt/fb-text-broadcast.txt", 'r');
if ($handle) {
  while (($buffer = fgets($handle, 4096)) !== false) {
    $message_body .= $buffer;
  }
  
  if (!feof($handle)) {
    $message_body = "__(FGETS-EFFED-UP)__";
  }
  
  fclose($handle);
}


// matty's fb id
//$user_obj['chat_id'] = "1219553058088713";
//$query = 'SELECT DISTINCT `chat_id` FROM `fbbot_logs` WHERE `chat_id` = "1219553058088713" LIMIT 1;';

$query = 'SELECT DISTINCT `chat_id` FROM `fbbot_logs`;';
$result = mysqli_query($db_conn, $query);

while ($user_obj = mysqli_fetch_object($result)) {
  echo ("FB --> ". $user_obj->chat_id ."\n");
  $payload_arr = array(
		'recipient' => array(
			'id' => $user_obj->chat_id
		),
		'message' => array(
		  'text' => (strlen($message_body) > 0) ? $message_body : "__(TXT-AINT-HERE)__"
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
