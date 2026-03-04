package main

import (
	"database/sql"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"os"
	"strconv"

	_ "github.com/go-sql-driver/mysql"
)

type Channel struct {
	ID       int64
	Title    string
	Username sql.NullString
}

type Message struct {
	MessageID   int64
	Text        sql.NullString
	MediaURL    sql.NullString
	PublishedAt string
}

type ChannelsPageData struct {
	Channels []Channel
}

type MessagesPageData struct {
	Channels       []Channel
	CurrentChannel Channel
	Messages       []Message
	Page           int
	TotalPages     int
	HasPrev        bool
	HasNext        bool
	PrevPage       int
	NextPage       int
}

func main() {
	db, err := openDBFromEnv()
	if err != nil {
		log.Fatalf("open DB: %v", err)
	}
	defer db.Close()

	tmplLayout := template.Must(template.ParseFiles(
		"templates/layout.html",
	))
	tmplChannels := template.Must(template.Must(tmplLayout.Clone()).ParseFiles(
		"templates/layout.html",
		"templates/channels.html",
	))
	tmplMessages := template.Must(template.Must(tmplLayout.Clone()).ParseFiles(
		"templates/layout.html",
		"templates/messages.html",
	))

	mux := http.NewServeMux()

	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		channels, err := loadChannels(db)
		if err != nil {
			http.Error(w, "failed to load channels", http.StatusInternalServerError)
			log.Printf("loadChannels: %v", err)
			return
		}

		data := ChannelsPageData{
			Channels: channels,
		}
		if err := tmplChannels.ExecuteTemplate(w, "layout", data); err != nil {
			log.Printf("render channels: %v", err)
		}
	})

	mux.HandleFunc("/channels", func(w http.ResponseWriter, r *http.Request) {
		q := r.URL.Query()
		idStr := q.Get("id")
		if idStr == "" {
			http.Redirect(w, r, "/", http.StatusFound)
			return
		}
		channelID, err := strconv.ParseInt(idStr, 10, 64)
		if err != nil {
			http.Error(w, "invalid channel id", http.StatusBadRequest)
			return
		}
		page := 1
		if pStr := q.Get("page"); pStr != "" {
			if p, err := strconv.Atoi(pStr); err == nil && p > 0 {
				page = p
			}
		}
		const perPage = 50

		channels, err := loadChannels(db)
		if err != nil {
			http.Error(w, "failed to load channels", http.StatusInternalServerError)
			log.Printf("loadChannels: %v", err)
			return
		}

		cur, err := loadChannelByID(db, channelID)
		if err != nil {
			http.Error(w, "channel not found", http.StatusNotFound)
			return
		}

		totalMessages, err := countMessages(db, channelID)
		if err != nil {
			http.Error(w, "failed to count messages", http.StatusInternalServerError)
			log.Printf("countMessages: %v", err)
			return
		}
		totalPages := 1
		if totalMessages > 0 {
			totalPages = int((totalMessages + perPage - 1) / perPage)
		}
		if page > totalPages {
			page = totalPages
		}
		offset := (page - 1) * perPage

		msgs, err := loadMessages(db, channelID, perPage, offset)
		if err != nil {
			http.Error(w, "failed to load messages", http.StatusInternalServerError)
			log.Printf("loadMessages: %v", err)
			return
		}

		data := MessagesPageData{
			Channels:       channels,
			CurrentChannel: cur,
			Messages:       msgs,
			Page:           page,
			TotalPages:     totalPages,
			HasPrev:        page > 1,
			HasNext:        page < totalPages,
			PrevPage:       page - 1,
			NextPage:       page + 1,
		}
		if err := tmplMessages.ExecuteTemplate(w, "layout", data); err != nil {
			log.Printf("render messages: %v", err)
		}
	})

	addr := ":8080"
	log.Printf("Go web app listening on http://localhost%s", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("ListenAndServe: %v", err)
	}
}

func openDBFromEnv() (*sql.DB, error) {
	host := getenvDefault("DB_HOST", "localhost")
	port := getenvDefault("DB_PORT", "3306")
	name := getenvDefault("DB_NAME", "telegram_reader")
	user := getenvDefault("DB_USER", "tgbg")
	pass := getenvDefault("DB_PASSWORD", "")

	dsn := fmt.Sprintf("%s:%s@tcp(%s:%s)/%s?parseTime=true&charset=utf8mb4&loc=Local",
		user, pass, host, port, name)
	return sql.Open("mysql", dsn)
}

func getenvDefault(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func loadChannels(db *sql.DB) ([]Channel, error) {
	rows, err := db.Query(`SELECT id, title, username FROM channels ORDER BY title ASC`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var result []Channel
	for rows.Next() {
		var ch Channel
		if err := rows.Scan(&ch.ID, &ch.Title, &ch.Username); err != nil {
			return nil, err
		}
		result = append(result, ch)
	}
	return result, rows.Err()
}

func loadChannelByID(db *sql.DB, id int64) (Channel, error) {
	row := db.QueryRow(`SELECT id, title, username FROM channels WHERE id = ?`, id)
	var ch Channel
	if err := row.Scan(&ch.ID, &ch.Title, &ch.Username); err != nil {
		return Channel{}, err
	}
	return ch, nil
}

func countMessages(db *sql.DB, channelID int64) (int64, error) {
	row := db.QueryRow(`SELECT COUNT(*) FROM messages WHERE channel_id = ?`, channelID)
	var n int64
	if err := row.Scan(&n); err != nil {
		return 0, err
	}
	return n, nil
}

func loadMessages(db *sql.DB, channelID int64, limit, offset int) ([]Message, error) {
	rows, err := db.Query(
		`SELECT message_id, text, media_url, published_at
         FROM messages
         WHERE channel_id = ?
         ORDER BY published_at DESC
         LIMIT ? OFFSET ?`,
		channelID, limit, offset,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var result []Message
	for rows.Next() {
		var m Message
		if err := rows.Scan(&m.MessageID, &m.Text, &m.MediaURL, &m.PublishedAt); err != nil {
			return nil, err
		}
		result = append(result, m)
	}
	return result, rows.Err()
}

