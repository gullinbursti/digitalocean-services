<?php 

// db creds
define('DB_HOST', "external-db.s4086.gridserver.com");
define('DB_NAME', "db4086_modd");
define('DB_USER', "db4086_modd_usr");
define('DB_PASS', "f4zeHUga.age");

// bot info
define('BROADCASTER_ADDR', "162.243.150.21");
define('BROADCASTER_USER_AGENT', "GameBots-Broadcaster-v3");
define('KIKBOT_HOST', "http://159.203.250.4:8080");
define('KIKBOT_WEBHOOK', "/product-notify");
define('KIKBOT_BROADCAST_TOKEN', "326d665bbc91c22b4f4c18a64e577183");
define('KIKBOT_MESSAGE_TEMPLATE_PATH', "/opt/cron/etc/kik-product_broadcast.conf");
define('KIKBOT_ORTHODOX_MESSAGE_TEMPLATE', '_{PRODUCT_NAME}_ went on pre-sale _{HOURS}_h _{MINUTES}_m _{SECONDS}_s ago for $_{PRICE}_.');
define('KIKBOT_PRODUCT_ATTRIBUTION', "game.bots");
define('STRIPE_URL_TEMPLATE', 'http://prekey.co/stripe/_{PRODUCT_ID}_/_{TO_USER}_');


// make the connection
$db_conn = mysqli_connect(DB_HOST, DB_USER, DB_PASS) or die("Could not connect to database\n");

// select the proper db
mysqli_select_db($db_conn, DB_NAME) or die("Could not select database\n");
mysqli_set_charset($db_conn, 'utf8');


// select closest to date - 24h
$query = 'SELECT `id`, `name`, `price`, `image_url`, `added` FROM `fb_products` WHERE `enabled` = 1 LIMIT 1;';
$result = mysqli_query($db_conn, $query);

// nothing found
if (mysqli_num_rows($result) == 0) {
  mysqli_free_result($result);
  exit();
}

// today's product
$product_obj = mysqli_fetch_object($result);

// calc time diff
$date1 = new DateTime($product_obj->added);
$date2 = new DateTime("now");
$interval = $date1->diff($date2);

// open txt 1-liner for template
$message_template = KIKBOT_ORTHODOX_MESSAGE_TEMPLATE;
$handle = @fopen(KIKBOT_MESSAGE_TEMPLATE_PATH, 'r');
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
    $message_template = KIKBOT_ORTHODOX_MESSAGE_TEMPLATE;
  }

  fclose($handle);
  
} else {
  echo("Couldn't open template file, using default: ". KIKBOT_ORTHODOX_MESSAGE_TEMPLATE);
}


// replace template tokens w/ content
$body_txt = preg_replace('/_\{PRODUCT_NAME\}_/', $product_obj->name, $message_template);
$body_txt = preg_replace('/_\{PRICE\}_/', $product_obj->price, $body_txt);
$body_txt = preg_replace('/_\{HOURS\}_/', $interval->h, $body_txt);
$body_txt = preg_replace('/_\{MINUTES\}_/', $interval->m, $body_txt);
$body_txt = preg_replace('/_\{SECONDS\}_/', $interval->s, $body_txt);
$stripe_url = preg_replace('/_\{PRODUCT_ID\}_/', $product_obj->id, STRIPE_URL_TEMPLATE);

// use defined name as argv 'php kik-product-broadcast.php "btzDoh"'
$query = (count($argv) == 2) ? 'SELECT `username`, `chat_id` FROM `kikbot_logs` WHERE `username` = "'. $argv[1] .'" LIMIT 1;' : 'SELECT DISTINCT(`username`), `chat_id` FROM `kikbot_logs` WHERE `id` > 105499;';
$result = mysqli_query($db_conn, $query);

echo("Sending to ". number_format(mysqli_num_rows($result)) ." total users w/ message: \"". $body_txt ."\" & card image: [". $product_obj->image_url ."]\n[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]\n");

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
      'item_url'   => "http://kik.me/game.bots",//preg_replace('/_\{TO_USER\}_/', $user_obj->username, $stripe_url),
      'body_txt'   => $body_txt,
      'attrib_txt' => KIKBOT_PRODUCT_ATTRIBUTION
    )),
    CURLOPT_URL => KIKBOT_HOST . KIKBOT_WEBHOOK
  ));
  
  // result & close
  $r = curl_exec($ch);
  curl_close($ch);
}

mysqli_free_result($result);

// close db
if ($db_conn) {
	mysqli_close($db_conn);
	$db_conn = null;
}
?>