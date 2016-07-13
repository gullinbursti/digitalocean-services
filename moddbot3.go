package main

import (
	"encoding/json"
	"fmt"
	"github.com/gorilla/mux"
	"go-ircevent"
//	"html"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"regexp"
	"strings"
	"time"
)

//var userName = "faroutrob"
//var roomName = "#" + userName
var (
	con *irc.Connection
	subscribersForStreamer map[string][]string
)


var schema = `
        CREATE TABLE streamer (
        username text,
        );
`

type Streamer struct {
        UserName string `db:"username"`
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




func main() {
	fmt.Println("yo")
	con = irc.IRC("gamebotsc", "gamebotsc") //nick, user
	con.Password = "oauth:tc0t646rjaavm29tooodo68ca9lmxr"

	var result []string

	var timeTable = map[string]time.Time{} //{"faroutrob": time.Now(), "matty_devdev": time.Now(), "moddtester": time.Now()}
	var modTable = map[string]int{}        //{"faroutrob": 0, "matty_devdev": 0, "moddtester": 0}

	response, err := http.Get("http://beta.modd.live/api/irc_channels.php")
	if err != nil {
		//		fmt.Printf("%s", err)
		os.Exit(1)
	} else {
		defer response.Body.Close()
		contents, err := ioutil.ReadAll(response.Body)
		if err != nil {
			//			fmt.Printf("%s", err)
			os.Exit(1)
		}
		result = strings.Split(string(contents), "\n")
		for i := range result {
			//			fmt.Println(result[i])
			timeTable[result[i]] = time.Now()
			modTable[result[i]] = 0
		}
	}
	///////////////////////////////////////

	con.AddCallback("001", func(e *irc.Event) {
		fmt.Println("001")
		for i := range result {
			con.Join("#" + result[i])
		}
	})
	con.AddCallback("JOIN", func(e *irc.Event) {
		//		room := e.Arguments[0]
		//		con.Privmsg(room, "")
	})

	con.AddCallback("PRIVMSG", func(e *irc.Event) {
		return
		room := e.Arguments[0]
		nick := room[1:len(room)]
		if modTable[nick] == 2 { // skip over users who un-modded moddbot
			return
		}
		if nick == "streamcard" {
			return
		}

		timeTable[nick] = time.Now()
		//		fmt.Println("roomname = " + room)
		//		fmt.Println("privmsg")
		subscribe := regexp.MustCompile(`(?i)!subscribe`)
		support := regexp.MustCompile(`(?i)!support`)
		moddhelp := regexp.MustCompile(`(?i)!moddhelp`)
		highlight := regexp.MustCompile(`(?i)!highlight`)
		var msg = e.Message()

		switch {
		case subscribe.MatchString(msg):
			//Analytics call
			_, err := http.Get("http://beta.modd.live/api/irc_message.php?channel=" + nick + "&command=subscribe")
			if err != nil {
			} //END Analytics call
			con.Privmsg(room, "Subscribe to my stream moments and receive updates when I am live. Click here:  s.00m.co/"+nick)
		case support.MatchString(msg):
			//Analytics call
			_, err := http.Get("http://beta.modd.live/api/irc_message.php?channel=" + nick + "&command=support")
			if err != nil {
			} //END Analytics call

			response, err := http.Get("http://beta.modd.live/api/bot_url.php?type=promo&name=" + nick)
			if err != nil {
				//fmt.Printf("%s", err)
				os.Exit(1)
			} else {

				defer response.Body.Close()
				contents, err := ioutil.ReadAll(response.Body)
				if err != nil {
					//fmt.Printf("%s", err)
					os.Exit(1)
				} else {
					con.Privmsg(room, string(contents))
					//fmt.Println("yo" + "http://beta.modd.live/api/bot_url.php?type=game&name=" + nick)
				}
			}

		case moddhelp.MatchString(msg):
			//Analytics call
			_, err := http.Get("http://beta.modd.live/api/irc_message.php?channel=" + nick + "&command=help")
			if err != nil {
			} //END Analytics call

			con.Privmsg(room, "beta.modd.live/help.html")

		case highlight.MatchString(msg):
			//Analytics call
			_, err := http.Get("http://beta.modd.live/api/irc_message.php?channel=" + nick + "&command=highlight")
			if err != nil {
			} //END Analytics call

			con.Privmsg(room, "highlight")
		default:
			//			fmt.Println("is not recognized")
		}
		//		fmt.Println(msg)

	})

	ircerr := con.Connect("irc.chat.twitch.tv:6667")
	if ircerr != nil {
		fmt.Println("Failed connecting")
		return
	}

	messageTicker := time.NewTicker(time.Millisecond * 7200000)
	//	lastTime := time.Now()
	go func() {
		for t := range messageTicker.C {
			fmt.Println(t)
			//loop through message timeTable for users and if no  messages within the hour send out subscribe, gamecard and/or cross promote round robin
			for subscriber := range result {
				if modTable[result[subscriber]] == 2 { // skip over users who un-modded moddbot
					continue
				}
				//response2, err2 := http.Get("https://api.twitch.tv/kraken/streams/")
				///////////////////////////////////////
				response, err := http.Get("https://api.twitch.tv/kraken/streams/" + result[subscriber])
				if err != nil {
					//fmt.Printf("%s", err)
					//os.Exit(1)
					return
				}
				defer response.Body.Close()
				contents, err1 := ioutil.ReadAll(response.Body)
				if err1 != nil {
					//fmt.Printf("%s", err1)
					//os.Exit(1)
					return
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
					return
				} else {
					if m.Stream.Id != 0 { //if online
						
						con.Privmsg("#"+result[subscriber], "Subscribe to my stream moments and receive updates when I am live. Click here:  s.00m.co/username")
						//}
					}
				}

				//						fmt.Println(string(contents))

			}
		}
	}()

	addUserTicker := time.NewTicker(time.Millisecond * 360000)
	go func() {
		for j2 := range addUserTicker.C {
			fmt.Println(j2)

			response, err := http.Get("http://beta.modd.live/api/irc_channels.php")
			if err != nil {
				//fmt.Printf("%s", err)
				os.Exit(1)
			} else {
				defer response.Body.Close()
				contents, err := ioutil.ReadAll(response.Body)
				if err != nil {
					fmt.Printf("%s", err)
					os.Exit(1)
				}
				newResultSet := strings.Split(string(contents), "\n")
				//fmt.Println("looping through new Set")
				for i := range newResultSet {

					//	fmt.Println(newResultSet[i])
					_, present := timeTable[newResultSet[i]]
					if !present {
						//		fmt.Println("adding")
						con.Join("#" + newResultSet[i])
						result = append(result, newResultSet[i])
						timeTable[newResultSet[i]] = time.Now()
						modTable[newResultSet[i]] = 0
					}
				}
			}
		}

	}()

	otherTicker := time.NewTicker(time.Millisecond * 360000)
	lastTime := time.Now()
	go func() {
		for t2 := range otherTicker.C {
			fmt.Println(lastTime.Sub(t2).Seconds())
			//if  modTable[user] == 0 and moddbot shows as moderator then set modTable[user] to 1 and message "moddbot has been activate"
			//if modTble[user == 1 and  moddbot does NOT show up as moderator then exit the channel and set to 2

			for subscriber := range result {
				if modTable[result[subscriber]] == 2 {
					continue
				}
				response, err := http.Get("http://tmi.twitch.tv/group/user/" + result[subscriber] + "/chatters")
				if err != nil {
							fmt.Printf("%s", err)
					//os.Exit(1)
					return
				}
				defer response.Body.Close()
				contents, err1 := ioutil.ReadAll(response.Body)
				if err1 != nil {
							fmt.Printf("%s", err1)
					//os.Exit(1)
					//return
				} else {
					type chattersJson struct {
						Chatters struct {
							Mods []string `json:"moderators"`
						} `json:"chatters"`
					}
					var chatters chattersJson
					err2 := json.Unmarshal(contents, &chatters)
					if err2 != nil {
									fmt.Printf("%s", err2)
						//os.Exit(1)
						return
					} else {
						hasmoddbot := false
						for x := range chatters.Chatters.Mods {
							if chatters.Chatters.Mods[x] == "mbtester" {
								hasmoddbot = true
							}
							//				fmt.Println(chatters.Chatters.Mods[x])
						}
						if modTable[result[subscriber]] == 0 && hasmoddbot {
							con.Privmsg("#"+result[subscriber], "Welcome to MODD. If you need help type !moddHelp. More details can be found at www.modd.live")
							modTable[result[subscriber]] = 1
						}
						if modTable[result[subscriber]] == 1 && !hasmoddbot {
							con.Privmsg("#"+result[subscriber], "Goodbye cruel world!")
							modTable[result[subscriber]] = 2
						}
					}
				}
			}
		}
	}()

	go con.Loop()

	router := mux.NewRouter().StrictSlash(true)
	router.HandleFunc("/{usr}/{usrmsg}", Message)
	router.HandleFunc("/w/{usr}/{usrmsg}", WhisperMessage)
	log.Fatal(http.ListenAndServe(":8080", router))

}

func Message(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	usr := vars["usr"]
	usrmsg := vars["usrmsg"]
	w.Header().Set("Access-Control-Allow-Origin", "*")
	//fmt.Fprintln(w, "", usr)
	//fmt.Fprintf(w, "", html.EscapeString(r.URL.Path))
	//Analytics call
	_, err := http.Get("http://beta.modd.live/api/irc_message.php?channel=" + usr + "&command=subscribe")
	if err != nil {
	} //END Analytics call

	con.Privmsg("#"+usr, usrmsg)
}

func WhisperMessage(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	usr := vars["usr"]
	usrmsg := vars["usrmsg"]
	w.Header().Set("Access-Control-Allow-Origin", "*")
	//fmt.Fprintln(w, "", usr)
	//fmt.Fprintf(w, "", html.EscapeString(r.URL.Path))
	//Analytics call
//	_, err := http.Get("http://beta.modd.live/api/irc_message.php?channel=" + usr + "&command=subscribe")
//	if err != nil {
//	} //END Analytics call
	//con.Privmsg("#"+usr, "whisper")

	con.Privmsg("#"+usr, ".w "+usr+" "+usrmsg)
}

/*
func WhisperMessage(w http.ResponseWriter, r *http.Request) {
        vars := mux.Vars(r)
        usr := vars["streamer"]
        usrmsg := vars["usrmsg"]
        w.Header().Set("Access-Control-Allow-Origin", "*")

 cids := subscribersForStreamer[streamer]
        fmt.Println(subscribersForStreamer) 
        fmt.Println(streamer + " " + usrmsg + " ")
        fmt.Println(cids)
        for i := range cids {
*/