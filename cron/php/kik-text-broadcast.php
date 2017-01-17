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

$message = "";
$handle = @fopen("/opt/modd/etc/kik-text-broadcast.conf", 'r');
if ($handle) {
  while (($buffer = fgets($handle, 4096)) !== false) {
    $message .= $buffer;
  }

  if (!feof($handle)) {
    $message = "Did you know you can win Frontside Misty's in Gamebots Facebook chatbot?\n\nm.me/gamebotsc\nFacebook.com/gamebotsc";
  }

  fclose($handle);
}

if (strlen($message) == 0) {
  $message = "Did you know you can win Frontside Misty's in Gamebots Facebook chatbot?\n\nm.me/gamebotsc\nFacebook.com/gamebotsc";
}

// select gamebots users
$query = 'SELECT DISTINCT(`username`), `chat_id` FROM `kikbot_logs`;';
$result = mysqli_query($db_conn, $query);

while ($user_obj = mysqli_fetch_object($result)) {
  echo ("KIK {txt}--> ". $user_obj->username ."\n");

  $curl = curl_init();
  curl_setopt_array($curl, array(
    CURLOPT_USERAGENT => "GameBots-Tracker-v2",
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_POST => 1,
    CURLOPT_POSTFIELDS => http_build_query(array(
      'token' => "f7d3612391b5ba4d89d861bea6283726",
      'to_user' => $user_obj->username,
      'chat_id' => $user_obj->chat_id,
      'message' => $message
    )),
    CURLOPT_URL => "http://159.203.250.4:8080/message"
  ));

  $r = curl_exec($curl);
  curl_close($curl);
}

?>
