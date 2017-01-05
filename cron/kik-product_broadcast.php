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

// select closest to date - 24h
$query = 'SELECT `id`, `name`, `price`, `image_url`, `added` FROM `fb_products` WHERE `added` > DATE_SUB(NOW(), INTERVAL 24 HOUR) ORDER BY `added` LIMIT 1;';
$result = mysqli_query($db_conn, $query);
$product_obj = mysqli_fetch_object($result);
mysqli_free_result($result);

$date1 = new DateTime($product_obj->added);
$date2 = new DateTime("now");
$interval = $date1->diff($date2);

$query = 'SELECT DISTINCT(`username`), `chat_id` FROM `kikbot_logs`;';
$result = mysqli_query($db_conn, $query);

while ($user_obj = mysqli_fetch_object($result)) {
  echo ("KIK --> ". $user_obj->username ."\n");

  $curl = curl_init();
  curl_setopt_array($curl, array(
    CURLOPT_USERAGENT => "GameBots-Tracker-v2",
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_POST => 1,
    CURLOPT_POSTFIELDS => http_build_query(array(
      'token' => "326d665bbc91c22b4f4c18a64e577183",
      'from_user' => $user_obj->username,
      'chat_id' => $user_obj->chat_id,
      'item_name' => $product_obj->name,
      'price' => $product_obj->price,
      'message' => $product_obj->name ." went on sale for $". $product_obj->price ." ". $interval->h ."h ". $interval->i ."m ". $interval->s ."s ago."
    )),
    CURLOPT_URL => "http://159.203.250.4:8080/product-notify"
  ));

  $r = curl_exec($curl);
  curl_close($curl);
}

?>
