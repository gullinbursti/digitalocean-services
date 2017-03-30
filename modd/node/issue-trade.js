/**
 * STOREHOUSE - node-steamcommunity
 *
 * Uses node-steamcommunity to login to Steam, accept and confirm all incoming trade offers,
 *    node-steam-totp to generate 2FA codes
 */

var SteamCommunity = require('steamcommunity');
var SteamTotp = require('steam-totp');
var TradeOfferManager = require('../lib/index.js'); // use require('steam-tradeoffer-manager') in production
var fs = require('fs');
var mysql = require('mysql');
var request = require('request');

var steam = new SteamCommunity();
var manager = new TradeOfferManager({
  "domain"       : "example.com", // Our domain is example.com
  "language"     : "en", // We want English item descriptions
  "pollInterval" : 5000 // We want to poll every 5 seconds since we don't have Steam notifying us of offers
});


var connection = mysql.createConnection({
  host     : 'external-db.s4086.gridserver.com',
  user     : 'db4086_modd_usr',
  password : 'f4zeHUga.age',
  database : 'db4086_modd'
});
connection.connect();


// Steam logon options
var logOnOptions = {
  "accountName"    : "teammodd",
  "password"       : "gkY!z}[H0u7",
  "twoFactorCode"  : SteamTotp.getAuthCode("uJ4IvbWUg9RdMG5m/OqtYfTKE6w=")
};

if (fs.existsSync('steamguard.txt')) {
  logOnOptions.steamguard = fs.readFileSync('steamguard.txt').toString('utf8');
}

if (fs.existsSync('polldata.json')) {
  manager.pollData = JSON.parse(fs.readFileSync('polldata.json'));
}

steam.login(logOnOptions, function(err, sessionID, cookies, steamguard) {
  if (err) {
    console.log("Steam login fail: " + err.message);
    process.exit(1);
  }

  fs.writeFile('steamguard.txt', steamguard);

  console.log("Logged into Steam");
  manager.setCookies(cookies, function(err) {
    if (err) {
      console.log(err);
      process.exit(1); // Fatal error since we couldn't get our API key
      return;
    }

    console.log("Got API key: " + manager.apiKey);
  });

  sendTradeOffer()
});


manager.on('pollData', function(pollData) {
  fs.writeFile('polldata.json', JSON.stringify(pollData), function() {});
});



// send a trade offer
function sendTradeOffer() {
  console.log("sendTradeOffer()");

  // load inventory
  console.log('StatusMsg : Loading inventory...');
  manager.getInventoryContents(730, 2, true, function(error, inventory, currencies) {
    // failed to load inventory
    if(error) {
      console.log('\nError: Failed to load inventory\n');
      console.log(error);
      return;
    }

    // empty inventory
    if(inventory.length === 0) {
      console.log('StatusMsg : No tradable items found in inventory');
      // acknowledge admin
      client.chatMessage(config.admin, 'Sorry! I don\'t have any item to send.');
      return;
    }

    // inventory loaded
    console.log('StatusMsg : Total ' + inventory.length + ' tradable items found in inventory');

    connection.query('SELECT `item_winners`.`id`, `item_winners`.`fb_id`, `item_winners`.`trade_url`, `item_winners`.`prebot_url`, `flip_inventory`.`name`, `flip_inventory`.`asset_id` FROM `item_winners` INNER JOIN `flip_inventory` ON `item_winners`.`item_id` = `flip_inventory`.`id` WHERE `item_winners`.`claimed` = 0 AND `item_winners`.`trade_url` != "" AND `item_winners`.`prebot_url` != "" AND `item_winners`.`added` >= DATE_SUB(NOW(), INTERVAL 3 HOUR) ORDER BY `item_winners`.`added` LIMIT 1;', function(err, rows, fields) {
      if (!err) {
        for (var i=0; i<rows.length; i++) {
          var win_id = rows[i].id;
          var fb_psid = rows[i].fb_id;
          var trade_url = rows[i].trade_url;
          var prebot_url = rows[i].prebot_url;
          var item_name = rows[i].name;
          var asset_id = rows[i].asset_id;

          request.post({
            url  : "http://prebot.me/api/api.php",
            form : {
              ACCESS_TOKEN : "6849858F2449BCBF62D0309B8D2A7F03726A861F79D8C559400E551312812B3450EF0",
              action       : "VALIDATE_PRODUCT",
              prebot_url   : prebot_url
          }}, function(e, resp, body) {
            body = JSON.parse(body);
            if (body.result) {
              console.log('CREATING ['+asset_id+']--> '+item_name+' ('+trade_url+')');

              ind = -1;
              for (var j=0; j<inventory.length; j++) {
                if (inventory[j].assetid == asset_id) {
                  ind = j;
                  break;
                }
              }

              if (ind != -1) {
                // create a trade offer
                var offer = manager.createOffer(trade_url);
                offer.addMyItem(inventory[ind]);

                // send the trade offer
                offer.send(function(error, status) {
                  // failed to send the trade offer
                  if(error) {
                    console.log('\nError: Failed to send the trade offer\n');
                    console.log(error);
                    connection.query('UPDATE `item_winners` SET `claimed` = 1, `claim_date` = NOW() WHERE `id` = ? LIMIT 1;', [win_id], function(err2, rows2, fields2) {});
                    connection.end();
                    process.exit();
                    return;

                  } else if(status === 'pending') {
                    console.log('StatusMsg : The trade offer is sent but needs confirmation');
                    steam.acceptConfirmationForObject("cju/5tnWhDN6oJLqLQtxhinL0lo=", offer.id, function(error) {
                      // failed to confirm the trade offer
                      if(error) {
                        console.log('\nError: Failed to confirm the trade offer\n');
                        console.log(error);
                        connection.query('UPDATE `item_winners` SET `claimed` = 1, `claim_date` = NOW() WHERE `id` = ? LIMIT 1;', [win_id], function(err2, rows2, fields2) {});
                        connection.end();
                        process.exit();
                        return;

                      } else {
                        console.log('StatusMsg : The trade offer is confirmed');
                        //client.chatMessage(offer.partner.getSteamID64(), 'Yo! I have sent you ' + item_name);
                        connection.query('UPDATE `item_winners` SET `claimed` = 1, `claim_date` = NOW() WHERE `id` = ? LIMIT 1;', [win_id], function(err2, rows2, fields2) {});
                        connection.end();
                        process.exit();
                        return;
                      }
                    });

                  } else {
                    console.log('StatusMsg : The trade offer is sent');
                    //client.chatMessage(offer.partner.getSteamID64(), 'Yo! I have sent you ' + item_name);
                    connection.query('UPDATE `item_winners` SET `claimed` = 1, `claim_date` = NOW() WHERE `id` = ? LIMIT 1;', [win_id], function(err2, rows2, fields2) {});
                    connection.end();
                    process.exit();
                    return;
                  }
                });

              } else {
                connection.query('UPDATE `item_winners` SET `claimed` = 1, `claim_date` = NOW() WHERE `id` = ? LIMIT 1;', [win_id], function(err2, rows2, fields2) {});
                connection.end();
                process.exit();
              }

            } else {
              connection.query('UPDATE `item_winners` SET `claimed` = 1, `claim_date` = NOW() WHERE `id` = ? LIMIT 1;', [win_id], function(err2, rows2, fields2) {});
              connection.end();
              process.exit();
            }
          });
        }

      } else {
        console.log('ERROR!\n' + err);
      }
    });
    //connection.end();
  });
}