<?php 

// db creds
define('DB_HOST', "external-db.s4086.gridserver.com");
define('DB_NAME', "db4086_modd");
define('DB_USER', "db4086_modd_usr");
define('DB_PASS', "f4zeHUga.age");

// bot info
define('KIKBOT_HOST', "http://159.203.250.4:8080");
define('KIKBOT_WEBHOOK', "/product-notify");
define('KIKBOT_USER_AGENT', "GameBots-Broadcaster-v3");
define('KIKBOT_BROADCAST_TOKEN', "326d665bbc91c22b4f4c18a64e577183");
define('KIKBOT_ORTHODOX_MESSAGE_TEMPLATE', '_{PRODUCT_NAME}_ went on pre-sale _{HOURS}_h _{MINUTES}_m _{SECONDS}_s ago for $_{PRICE}_.');
define('KIKBOT_PRODUCT_ATTRIBUTION', "Tap to Reserve");
define('KIKBOT_STRIPE_TEMPLATE', 'http://prekey.co/stripe/_{PRODUCT_ID}_/_{TO_USER}_');


// make the connection
$db_conn = mysqli_connect(DB_HOST, DB_USER, DB_PASS) or die("Could not connect to database\n");

// select the proper db
mysqli_select_db($db_conn, DB_NAME) or die("Could not select database\n");
mysqli_set_charset($db_conn, 'utf8');


// select closest to date - 24h
$query = 'SELECT `id`, `name`, `price`, `image_url`, `enabled`, `added` FROM `fb_products` WHERE `added` > DATE_SUB(NOW(), INTERVAL 24 HOUR) ORDER BY `added` LIMIT 1;';
$result = mysqli_query($db_conn, $query);

if (mysqli_num_rows($result) == 0) {
  mysqli_free_result($result);
  exit();
}


$product_obj = mysqli_fetch_object($result);

// update today's product
if ($product_obj->enabled == 0) {
  // reset prev to disabled, make this one enabled
  $query = 'UPDATE `fb_products` SET `enabled` = 0 WHERE `enabled` = 1; ';
  $query .= 'UPDATE `fb_products` SET `enabled` = 1 WHERE `id` = '. $product_obj->id .' LIMIT 1;';
  $result = mysqli_query($db_conn, $query);
  mysqli_free_result($result);
}

// calc time diff
$date1 = new DateTime($product_obj->added);
$date2 = new DateTime("now");
$interval = $date1->diff($date2);

// open txt 1-liner for template
$message_template = KIKBOT_ORTHODOX_MESSAGE_TEMPLATE;
$handle = @fopen("/opt/modd/txt/kik-product-broadcast.txt", 'r');
if ($handle) {
  
  // read in the line
  while (($buffer = fgets($handle, 4096)) !== false) {
    $message .= $buffer;
  }

  // eof error
  if (!feof($handle)) {
    $message_template = KIKBOT_ORTHODOX_MESSAGE_TEMPLATE;
  }

  fclose($handle);
}

// use defined name as argv 'php kik-product-broadcast.php s "btzDoh"'
$query = (count($argv) == 3 && $argv[1] == "s") ? 'SELECT `username`, `chat_id` FROM `kikbot_logs` WHERE `username` = "'. $argv[2] .'" ORDER BY `added` DESC LIMIT 1;' : 'SELECT DISTINCT(`username`), `chat_id` FROM `kikbot_logs`;';
$result = mysqli_query($db_conn, $query);

// replace template tokens w/ content
$body_txt = preg_replace('/_\{PRODUCT_NAME\}_/', $product_obj->name, $message_template);
$body_txt = preg_replace('/_\{PRICE\}_/', $product_obj->price, $body_txt);
$body_txt = preg_replace('/_\{HOURS\}_/', $interval->h, $body_txt);
$body_txt = preg_replace('/_\{MINUTES\}_/', $interval->m, $body_txt);
$body_txt = preg_replace('/_\{SECONDS\}_/', $interval->s, $body_txt);
$stripe_url = preg_replace('/_\{PRODUCT_ID\}_/', $product_obj->id, KIKBOT_STRIPE_TEMPLATE);

echo("Sending to ". number_format(mysqli_num_rows($result)) ." total users w/ message: \"". $body_txt ."\" & card image: [". $product_obj->image_url ."]\n");

// iterate
$cnt = 0;
while ($user_obj = mysqli_fetch_object($result)) {

  // output status
  echo(sprintf("KIK ([%05s]/[%05s])--> [%-64s] \"%s\"\n", number_format(++$cnt), number_format(mysqli_num_rows($result)), $user_obj->chat_id, $user_obj->username));
  
  // curl off to webhook
  $ch = curl_init();
  curl_setopt_array($ch, array(
    CURLOPT_USERAGENT      => "GameBots-Broadcaster-v3",
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_POST           => 1,
    CURLOPT_POSTFIELDS     => http_build_query(array(
      'token'      => KIKBOT_BROADCAST_TOKEN,
      'from_user'  => $user_obj->username,
      'chat_id'    => $user_obj->chat_id,
      'item_id'    => $product_obj->id,
      'img_url'    => $product_obj->image_url,
      'item_url'   => preg_replace('/_\{TO_USER\}_/', $user_obj->username, $stripe_url),
      'body_txt'   => $body_txt,
      'attrib_txt' => KIKBOT_PRODUCT_ATTRIBUTION
    )),
    CURLOPT_URL => KIKBOT_HOST . KIKBOT_WEBHOOK
  ));
  
  // result & close
  $r = curl_exec($ch);
  curl_close($ch);
  
  
  $ch = curl_init();
  curl_setopt_array($ch, array(
  	CURLOPT_USERAGENT      => "GameBots-Broadcaster-v3",
  	CURLOPT_RETURNTRANSFER => true,
  	CURLOPT_URL            => "http://beta.modd.live/api/bot_tracker.php?src=kik&category=broadcast&action=broadcast&label=". $user_obj->chat_id ."&value=&cid=". md5($_SERVER['REMOTE_ADDR'])
  ));

  $r = curl_exec($ch);
  curl_close($ch);
  
  $ch = curl_init();
  curl_setopt_array($ch, array(
  	CURLOPT_USERAGENT      => "GameBots-Broadcaster-v3",
  	CURLOPT_RETURNTRANSFER => true,
  	CURLOPT_URL            => "http://beta.modd.live/api/bot_tracker.php?src=kik&category=user-message&action=user-message&label=". $user_obj->chat_id ."&value=&cid=". md5($_SERVER['REMOTE_ADDR'])
  ));

  $r = curl_exec($ch);
  curl_close($ch);
}

?>