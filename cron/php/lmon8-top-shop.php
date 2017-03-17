<?php

define('DB_HOST', "138.197.216.56");
define('DB_NAME', "prebot_marketplace");
define('DB_USER', "pre_usr");
define('DB_PASS', "f4zeHUga.age");

define('BROADCASTER_ADDR', "162.243.150.21");
define('BROADCASTER_USER_AGENT', "GameBots-Broadcaster-v3");
define('FB_MESSAGE_TEMPLATE_PATH', "/opt/cron/etc/". basename(__FILE__, ".php") .".conf");


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
      CURLOPT_URL            => sprintf("http://beta.modd.live/api/bot_tracker.php?src=facebook&category=%s&action=%s&label=%s&value=%d&cid=%s", $val['category'], $val['action'], $val['label'], $val['value'], $val['cid'])
    ));

    array_push($response_arr, curl_exec($ch));
    curl_close($ch);
  }
}

function post_message($url, $payload_obj) {
  echo (sprintf("Sending payload -->\n%s\n\n", json_encode($payload_obj)));

  $ch = curl_init();
  curl_setopt($ch, CURLOPT_URL, $url);
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


// make the connection
$db_conn = mysqli_connect(DB_HOST, DB_USER, DB_PASS) or die("Could not connect to database\n");

// select the proper db
mysqli_select_db($db_conn, DB_NAME) or die("Could not select database\n");
mysqli_set_charset($db_conn, 'utf8');



// open txt config for templates
$config_arr = array(
  'FB_GRAPH_API'     => "https://graph.facebook.com/v2.6/me/messages",
  'FB_ACCESS_TOKEN'  => "EAADzAMIzYPEBAJGk5P18ibMeEBhhdvUzZBsMoItnuB19PEzUGnNZALX5MN1rK0HKEfSG4YsmyVM2NmeK3m9wcmDvmwoB97aqfn1U0KOdvNtv6ZCgPLvqPFr2YbnlinuUUSrPtnphqafj6ad73wIPVBCOhCaiLGfvEZCUr7CxcAZDZD",
  'BODY_TEMPLATE'    => "Today's topumsub shop is %s\n\nTYPE \"%s\" to subscribe.",
  'BATCH_TEMPLATES'  => array()
);

$handle = @fopen(FB_MESSAGE_TEMPLATE_PATH, 'r');
if ($handle) {

  // read in the line
  while (($buffer = fgets($handle, 4096)) !== false) {
    if (preg_match('/^[#$]/i', $buffer) || preg_match('/^\s*$/i', $buffer)) {
      continue;

    } else {
      preg_match('/^(?P<key>[A-Z_]+)\t(?P<val>.*)$/', $buffer, $match_arr);
      $config_arr[$match_arr['key']] = $match_arr['val'];
    }
  }

  // eof error
  if (!feof($handle)) {
    //$message_template = FB_ORTHODOX_MESSAGE_TEMPLATE;
  }

  fclose($handle);

} else {
  echo("Couldn't open config file! ". FB_MESSAGE_TEMPLATE_PATH ."\n");
}


$body_txt = preg_replace('/__nl__/', "\n", $config_arr['BODY_TEMPLATE']);


// get list of recipients
$query = (count($argv) == 2) ? 'SELECT DISTINCT `user_id`, `fb_psid` FROM `fb_users` WHERE `fb_psid` = "'. $argv[1] .'" LIMIT 1;' : 'SELECT `user_id`, `fb_psid` FROM `fb_users` WHERE `opt_out` = 0;';
$result = mysqli_query($db_conn, $query);

// top subbed shop
$query = 'SELECT `storefront_id`, COUNT(*) AS `cnt` FROM `subscriptions` WHERE `enabled` = 1 AND `added` > DATE_SUB(NOW(), INTERVAL 24 HOUR) GROUP BY `storefront_id` ORDER BY `cnt` DESC LIMIT 1';
$res = mysqli_query($db_conn, $query);


if (mysqli_num_rows($res) == 0) {
  echo("No subscriptions for today!\n");
  exit(0);
}


$storefront_obj = mysqli_fetch_object($res);

$query = 'SELECT `id`, `display_name`, `prebot_url` FROM `products` WHERE `storefront_id` = '. $storefront_obj->storefront_id .' LIMIT 1;';
$res = mysqli_query($db_conn, $query);

if (mysqli_num_rows($res) == 1) {
  $product_obj = mysqli_fetch_object($res);

} else {
  echo("No subscriptions for today!\n");
  exit(0);
}

// summary
echo("Sending to ". number_format(mysqli_num_rows($result)) ." total users w/ message: \"". sprintf($body_txt, $product_obj->display_name, $storefront_obj->cnt, preg_replace('/^.*\/(.*)$/', 'm.me/lmon8?ref=/$1', $product_obj->prebot_url)) ."\"\n[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]\n");

// iterate
$cnt = 0;
while ($fb_user_obj = mysqli_fetch_object($result)) {

  // output status
  echo(sprintf("FB (%05s/%05s)--> [%-16s]\n", number_format(++$cnt), number_format(mysqli_num_rows($result)), $fb_user_obj->fb_psid));
  
  $element_arr = array();
  $query = 'SELECT `id`, `storefront_id`, `display_name`, `image_url`, `prebot_url` FROM `products` WHERE (`type` = 5 OR `type` = 6) AND `enabled` = 1 ORDER BY RAND() LIMIT 10;';
  $res = mysqli_query($db_conn, $query);
  while ($product_obj = mysqli_fetch_object($res)) {
    $query = 'SELECT `display_name` FROM `storefronts` WHERE `id` = '. $product_obj->storefront_id .' LIMIT 1;';
    $r = mysqli_query($db_conn, $query);
    $storefront_obj = mysqli_fetch_object($r);
    array_push($element_arr, array(
      'title'     => $storefront_obj->display_name, 
      'subtitle'  => $product_obj->display_name, 
      'image_url' => $product_obj->image_url, 
      'item_url'  => preg_replace('/^.*\/(.*)$/', 'm.me/lmon8?ref=/$1', $product_obj->prebot_url), 
      'buttons'   => array(
        array(
          'type'    => "postback",
          'payload' => sprintf("VIEW_PRODUCT-%d", $product_obj->id),
          'title'   => "View Shop"
        ),
        array(
          'type' => "element_share"
        )
      )
    ));
  }
  
  // build json array
  $payload_arr = array(
    'recipient' => array(
      'id' => $fb_user_obj->fb_psid
    ),
    'message'   => array(
      'attachment' => array(
        'type'    => "image",
        'payload' => array(
          'url' => "https://i.imgur.com/73iVUkb.gif"
        )
      )
    )
  );
  post_message($config_arr['FB_GRAPH_API'] ."?access_token=". $config_arr['FB_ACCESS_TOKEN'], $payload_arr);

  // build json array
  $payload_arr = array(
    'recipient' => array(
      'id' => $fb_user_obj->fb_psid
     ),
    'message'   => array(
      'text' => $body_txt
    )
  );
  post_message($config_arr['FB_GRAPH_API'] ."?access_token=". $config_arr['FB_ACCESS_TOKEN'], $payload_arr);
  
  // build json array
  $payload_arr = array(
    'recipient' => array(
      'id' => $fb_user_obj->fb_psid
     ),
    'message'   => array(
      'attachment'    => array(
        'type'    => "template",
        'payload' => array(
          'template_type' => "generic",
          'elements'      => $element_arr
        )
      ),
      'quick_replies' => array(
        array(
          'content_type' => "text",
          'title'        => "Main Menu",
          'payload'      => "MAIN_MENU"
        ),
        array(
          'content_type' => "text",
          'title'        => "Next Shop",
          'payload'      => "NEXT_STOREFRONT"
        ),
        array(
          'content_type' => "text",
          'title'        => "Feature Shop $1.99",
          'payload'      => "FEATURE_STOREFRONT"
        ),
        array(
          'content_type' => "text",
          'title'        => "Custom URL $0.99",
          'payload'      => "FEATURE_URL"
        )
      )
    )
  );
  post_message($config_arr['FB_GRAPH_API'] ."?access_token=". $config_arr['FB_ACCESS_TOKEN'], $payload_arr);
  send_tracker($fb_user_obj->fb_psid);
}

// close db
if ($db_conn) {
  mysqli_close($db_conn);
  $db_conn = null;
}

?>
