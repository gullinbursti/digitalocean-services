// This file provides a basic "quick start" example of using the Discordgo
// package to connect to Discord using the New() helper function.
package main

import (
	"encoding/json"
	"fmt"
	//	"html"
	"github.com/bwmarrin/discordgo"
	"github.com/gorilla/mux"
	"bytes"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"strings"
	//	"database/sql"
	_ "github.com/go-sql-driver/mysql"
	"github.com/jmoiron/sqlx"
	"encoding/csv"
)

var (
	discord *discordgo.Session
	subscribersForStreamer map[string][]string
	subscriberSeen map[string]string
)

var schema = `
        CREATE TABLE streamer (
        username text,
        );
`

type Streamer struct {
	UserName string `db:"username"`
}

func getStreamers() []string {

	db := sqlx.MustConnect("mysql", "db4086_modd_usr:f4zeHUga.age@tcp(external-db.s4086.gridserver.com:3306)/db4086_modd")

	rs := make([]string, 0)

	streamer := Streamer{}
	rows, _ := db.Queryx("SELECT `username` FROM `users` WHERE `type` = 'streamer';")
	for rows.Next() {
		err := rows.StructScan(&streamer)
		if err != nil {
			log.Fatalln(err)
		}
//		fmt.Println(streamer.UserName)
		rs = append(rs, strings.ToLower(streamer.UserName))
	}
	return rs

}

func isStreamerOnline(streamerName string) bool {
	response, err := http.Get("https://api.twitch.tv/kraken/streams/" + streamerName)
	if err != nil {
		//fmt.Printf("1%s", err)
		//os.Exit(1)
		return false
	}
	defer response.Body.Close()
	contents, err1 := ioutil.ReadAll(response.Body)
	if err1 != nil {
		//fmt.Printf("2%s", err1)
		//os.Exit(1)
		return false
	}
	type streamJson struct {
		Stream struct {
			Id int `json:"_id"`
		} `json:"stream"`
	}
	var m streamJson
	err2 := json.Unmarshal(contents, &m)
	if err2 != nil {
		//fmt.Printf("%s", err2)
		//os.Exit(1)
		return false
	} else {
		if m.Stream.Id != 0 { //if online
			return true
		}
	}

	return false
}

func getStreamerNameLink(theurl string) (string, string, string) {
	 response, err := http.Get(theurl)
        if err != nil {
                //os.Exit(1)
                return "", "", ""
        }
        defer response.Body.Close()
        contents, err1 := ioutil.ReadAll(response.Body)

        if err1 != nil {
                //os.Exit(1)
                return "", "", ""
        }
        type linkJson struct {
                        Channel string `json:"channel"`
			Preview_img string `json:"preview_img"`
			Player_url string `json:"player_url"`
        }
        var links linkJson
        err2 := json.Unmarshal(contents, &links)
        if err2 != nil {
                //os.Exit(1)
                return "", "", ""
        }
        return links.Channel, links.Preview_img, links.Player_url



}

/*
func getFollowers(streamerName string) int {
	response, err := http.Get("https://api.twitch.tv/kraken/channels/" + streamerName)
	//response, err := http.Get("https://api.twitch.tv/kraken/streams/" + streamerName)
	if err != nil {
		fmt.Printf("%s", err)
		//os.Exit(1)
		return -1
	}
	defer response.Body.Close()
	contents, err1 := ioutil.ReadAll(response.Body)
	if err1 != nil {
		fmt.Printf("%s", err1)
		//os.Exit(1)
		return -1
	}

	type streamJson struct {
                Stream struct {
			Id int `json:"_id"`
			Channel struct {
				followers string `json:"followers"`
			} `json:"channel"`
                } `json:"stream"`
        }

	type channelJson struct {
		Id int `json:"_id"`
		game string `json:"game"`
		followers int `json:"followers"`
	}
	var d channelJson
	err2 := json.Unmarshal(contents, &d)
	fmt.Println("!!!!! %s", d)
	if err2 != nil {
		fmt.Printf("%s", err2)
		//os.Exit(1)
		return -1
	} else {
		fmt.Println(streamerName)
		return 0//d.followers
	}
	return -1

}
*/



func main() {
	
        subscribersForStreamer = make(map[string][]string)
        streamerList := getStreamers()
        for subscriber := range streamerList {
                subscribersForStreamer[streamerList[subscriber]] = make([]string, 1)
        }

	//var subscribersForStreamer map[string][]string
//________________________
	response2, err := http.Get("http://beta.modd.live/api/subscriber_list.php?type=discord")


	csvfile, err := ioutil.ReadAll(response2.Body) //<--- here!

 	if err != nil {
 		fmt.Println(err)
 		os.Exit(1)
 	}

 	// print out
// 	fmt.Println(os.Stdout, string(htmlData)) //<-- here !
        


	//restore subscriptions from database
 	reader := csv.NewReader(bytes.NewReader(csvfile))

         reader.FieldsPerRecord = -1 // see the Reader struct information below

         rawCSVdata, err := reader.ReadAll()

         if err != nil {
                 fmt.Println(err)
                 os.Exit(1)
         }

         // sanity check, display to standard output
         for _, each := range rawCSVdata {
subscribersForStreamer[string(each[0])] = append(subscribersForStreamer[string(each[0])], string(each[2]))
//                 fmt.Printf("appending subscriber: %s to streamer : %s\n", each[1], each[0])
         }

//__________________________


//	fmt.Println(isStreamerOnline("anniefuchsia"))
	//getFollowers("faroutrob")
//	fmt.Println(getFollowers("anniefuchsia"))

	// Check for Username and Password CLI arguments.
	//if len(os.Args) != 3 {
	//	fmt.Println("You must provide username and password as arguments. See below example.")
	//	fmt.Println(os.Args[0], " [username] [password]")
//		return
//	}
	// Call the helper function New() passing username and password command
	// line arguments. This returns a new Discord session, authenticates,
	// connects to the Discord data websocket, and listens for events.
	//dg, err := discordgo.New("discord@modd.live", "Xz1hQwBIM*abc")
	dg, err := discordgo.New("gamebots@gamebots.chat", "gkY!z}[H0u7")
	discord = dg
	if err != nil {
		fmt.Println(err)
		return
	}
	// Register messageCreate as a callback for the messageCreate events.
	discord.AddHandler(messageCreate)
        discord.AddHandler(presenceUpdate)


	// Open the websocket and begin listening.
	discord.Open()
	router := mux.NewRouter().StrictSlash(true)
	router.HandleFunc("/{streamer}/{usrmsg}", Message)
	log.Fatal(http.ListenAndServe(":8080", router))

}


func presenceUpdate(s *discordgo.Session, m *discordgo.PresenceUpdate) {
//	fmt.Println("presenceUpdate")
//	fmt.Println(m.User.ID)
//	fmt.Println(m.User.Username)
     if _, ok := subscriberSeen[m.User.ID ]; ok {
	
     } else {
         if m.Status == "online" {
			 http.Get("http://beta.modd.live/api/bot_tracker.php?category=bot&action=signup&label=discord")
             //discord.ChannelMessageSend("192429730924986379", "Welcome to GameBots™, <@" + m.User.ID + ">!")
             //discord.ChannelMessageSend("192429730924986379", "Message <@192429415500742656> with an eSport player name or game you wish to subscribe.")
             discord.ChannelMessageSend("199265653205499904", "Welcome to GameBots™, <@" + m.User.ID + ">!")
              discord.ChannelMessageSend("199265653205499904", "Message <@197884191155683328> with an eSport player name or game you wish to subscribe.")
         }
    	subscriberSeen[m.User.ID] = ""
    }
}

// This function will be called (due to AddHandler above) every time a new
// message is created on any channel that the autenticated user has access to.
func messageCreate(s *discordgo.Session, m *discordgo.MessageCreate) {
	// Print message to stdout.
//	fmt.Println(m.ChannelID)
   // if "streamcard" == m.Author.Username {
	if "gamebots" == m.Author.Username {
//		fmt.Println("return")
		return
	}
	streamerLowerCase := strings.ToLower(m.Content)
//	fmt.Println(streamerLowerCase)
        //fmt.Println(m.Content)

	if strings.ToLower(m.Content) == "!all" {
		streamerList := getStreamers()
        for subscriber := range streamerList {
                http.Get("http://beta.modd.live/api/streamer_subscribe.php?type=discord&channel=" + streamerList[subscriber] + "&username=" + m.Author.Username + "&cid=" + m.ChannelID)
		    	subscribersForStreamer[streamerList[subscriber]] = append(subscribersForStreamer[streamerList[subscriber]], m.ChannelID)
				discord.ChannelMessageSend(m.ChannelID, "Subscribing to " + streamerList[subscriber] + fmt.Sprintf("%d", subscriber) + "/" + fmt.Sprintf("%d", len(streamerList)))
        }
	}


//	subscribersForStreamer
	if _, ok := subscribersForStreamer[streamerLowerCase]; ok {
        http.Get("http://beta.modd.live/api/streamer_subscribe.php?type=discord&channel=" + m.Content + "&username=" + m.Author.Username + "&cid=" + m.ChannelID)
		http.Get("http://beta.modd.live/api/bot_tracker.php?category=bot&action=subscribe&label=discord")
    		subscribersForStreamer[streamerLowerCase] = append(subscribersForStreamer[streamerLowerCase], m.ChannelID)
		
//		fmt.Println(subscribersForStreamer)
      discord.ChannelMessageSend(m.ChannelID, "Great! I found " + streamerLowerCase + ". You are subscribed to " + streamerLowerCase + "'s GameBots™ updates")
      discord.ChannelMessageSend(m.ChannelID, "Below are some top players that are live right now...")
      


		if isStreamerOnline(streamerLowerCase) {
 			a, b, c := getStreamerNameLink("http://beta.modd.live/api/live_streamer.php?channel=" + streamerLowerCase)
        		discord.ChannelMessageSend(m.ChannelID, (a + " is online and streaming!"))
        		discord.ChannelMessageSend(m.ChannelID, b)
        		discord.ChannelMessageSend(m.ChannelID, c)
		}
	} else
	{
         discord.ChannelMessageSend(m.ChannelID, "Oh no! I could not find a GameBots™ for " + streamerLowerCase + ". Enter an eSport player name or game you wish to subscribe.")
	}


//	fmt.Println(subscribersForStreamer)

}

func Message(w http.ResponseWriter, r *http.Request) {


	vars := mux.Vars(r)
	streamer := vars["streamer"]
	usrmsg := vars["usrmsg"]
	w.Header().Set("Access-Control-Allow-Origin", "*")
	cids := subscribersForStreamer[streamer]
//	fmt.Println(subscribersForStreamer) 
//	fmt.Println(streamer + " " + usrmsg + " ")
//	fmt.Println(cids)
	for i := range cids {
//		fmt.Println("sending message")
        	cid := cids[i]
		http.Get("http://beta.modd.live/api/bot_tracker.php?category=bot&action=send&label=discord")
		discord.ChannelMessageSend(cid, fmt.Sprintf(usrmsg))
   		_, b, c := getStreamerNameLink("http://beta.modd.live/api/live_streamer.php?channel=" + streamer)
                discord.ChannelMessageSend(cid, b)
                discord.ChannelMessageSend(cid, c)

        }
}
