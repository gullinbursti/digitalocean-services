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
  'FB_GRAPH_API'              => "https://graph.facebook.com/v2.6/me/messages",
  'FB_ACCESS_TOKEN'           => "EAADzAMIzYPEBAJGk5P18ibMeEBhhdvUzZBsMoItnuB19PEzUGnNZALX5MN1rK0HKEfSG4YsmyVM2NmeK3m9wcmDvmwoB97aqfn1U0KOdvNtv6ZCgPLvqPFr2YbnlinuUUSrPtnphqafj6ad73wIPVBCOhCaiLGfvEZCUr7CxcAZDZD",
  'STOREFRONT_OWNER_TEMPLATE' => "You have %s subs for %s.",
  'STOREFRONT_SUB_TEMPLATE'   => "The shop %s has %s subscribers",
  'INACTIVE_USER_TEMPLATE'    => "Today'a top sub shop is %s",
  'BATCH_TEMPLATES'           => array()
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


$owners_txt = $config_arr['STOREFRONT_OWNER_TEMPLATE'];
$subs_txt = $config_arr['STOREFRONT_SUB_TEMPLATE'];
$inactives_txt = $config_arr['INACTIVE_USER_TEMPLATE'];


// get list of recipients
$query = (count($argv) == 2) ? 'SELECT DISTINCT `user_id`, `fb_psid` FROM `fb_users` WHERE `fb_psid` = "'. $argv[1] .'" LIMIT 1;' : 'SELECT `user_id`, `fb_psid` FROM `fb_users` WHERE `opt_out` = 0 AND `id` > 1708;';
$result = mysqli_query($db_conn, $query);


// summary
echo("Sending to ". number_format(mysqli_num_rows($result)) ." total users w/ message: \"". $body_txt ."\"\n[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]\n");

// iterate
$cnt = 0;
while ($fb_user_obj = mysqli_fetch_object($result)) {
  
  // output status
  echo(sprintf("FB (%05s/%05s)--> [%-16s]\n", number_format(++$cnt), number_format(mysqli_num_rows($result)), $fb_user_obj->fb_psid));
  
  
  
  // check for active sf + prod
  $query = 'SELECT `storefronts`.`id` AS `storefront_id`, `products`.`id` AS `product_id`, `storefronts`.`display_name` AS `storefront_name`, `product`.`display_name` AS `product_name`, `products`.`prebot_url` AS `prebot_url` FROM `storefronts` INNER JOIN `products` ON `storefronts`.`id` = `products`.`storefront_id` WHERE `storefronts`.`owner_id` = "'. $fb_user_obj->user_id .'" AND `storefronts`.`enabled` = 1 AND `products`.`enabled` = 1 ORDER BY `products`.`added` DESC LIMIT 1;';
  $res = mysqli_query($db_conn, $query);
  
  $qr_arr = array(
    'content_type' => "text",
    'title'        => "Create Product",
    'payload'      => "CREATE_PRODUCT"
  )

  if (mysqli_num_rows($res) == 1) {
    $sf_prod_obj = mysqli_fetch_object($res);
    
    $query = 'SELECT COUNT(*) AS `tot` FROM `subscriptions` WHERE `storefront_id` = '. $sf_prod_obj->storefront_id .' AND `product_id` = '. $sf_prod_obj->product_id .' LIMIT 1;';
    $res = mysqli_query($db_conn, $query);
    
    if (mysqli_num_rows($res) == 1) {   
      $tot = mysqli_fetch_object($res)->tot;
      // build json array
      $payload_arr = array(
    		'recipient' => array(
    			'id'      => $fb_user_obj->fb_psid
    		),
    		'message' => array(
    		  'text'          => sprintf($config_arr['STOREFRONT_OWNER_TEMPLATE'], number_format($tot), $sf_prod_obj-storefront_name),
    		  'quick_replies' => $qr_array
        )
    	);
    	
    else {
      $query = 'SELECT COUNT(*) AS `tot` FROM `subscriptions` WHERE `user_id` = '. $fb_user_obj->user_id .';';
      $res = mysqli_query($db_conn, $query); 
      
      if (mysqli_num_rows($res) > 0) {    
        // build json array
        $payload_arr = array(
      		'recipient' => array(
      			'id'      => $fb_user_obj->fb_psid
      		),
      		'message' => array(
      		  'text'          => sprintf($config_arr['STOREFRONT_SUB_TEMPLATE'], ),
      		  'quick_replies' => $qr_array
          )
      	);
    }
  	
     
   // missing 
  } else {
    $query = 'SELECT `id` FROM `storefronts` WHERE `owner_id` = '. $fb_user_obj->user_id .' AND `enabled` = 1 ORDER BY `added` DESC LIMIT 1;';
    $res = mysqli_query($db_conn, $query);
    array_push($qr_array, array(
      'content_type' => "text",
      'title'        => "Create Shop",
      'payload'      => "CREATE_STOREFRONT"
    ));

    // no storefront
    if (mysqli_num_rows($res) == 0) {      
      array_push($qr_array, array(
        'content_type' => "text",
        'title'        => "Create Shop",
        'payload'      => "CREATE_STOREFRONT"
      ));
    
    // check product
    } else {
      $query = 'SELECT `id` FROM `products` WHERE `storefront_id` = '. $fb_user_obj->storefront_id .' AND `enabled = 1 ORDER BY `added` DESC LIMIT 1;';
      $res = mysqli_query($db_conn, $query);
      
      // missing product
      if (mysqli_num_rows($res) == 0) {
        array_push($qr_array, );
      }
    }
  }
  
  
  
  // build json array
  $payload_arr = array(
		'recipient' => array(
			'id'      => $fb_user_obj->fb_psid
		),
		'message' => array(
		  'text'          => $body_txt,
		  'quick_replies' => $qr_array
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
