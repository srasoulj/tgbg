package main

import (
	"database/sql"
	"fmt"
	"html"
	"html/template"
	"log"
	"net/http"
	"os"
	"regexp"
	"strconv"
	"time"

	_ "github.com/go-sql-driver/mysql"
	"github.com/joho/godotenv"
	ptime "github.com/yaa110/go-persian-calendar"
)

type Channel struct {
	ID       int64
	Title    string
	Username sql.NullString
}

type Message struct {
	MessageID         int64
	Text              sql.NullString
	MediaURL          sql.NullString
	AttachmentFileName sql.NullString // original filename for .npvt download link
	PublishedAt       time.Time
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
	// Load .env from current directory if present, overriding existing env vars.
	_ = godotenv.Overload(".env")

	db, err := openDBFromEnv()
	if err != nil {
		log.Fatalf("open DB: %v", err)
	}
	defer db.Close()

	_, tmplChannels, tmplMessages := buildTemplates()

	mux := http.NewServeMux()

	// Local static assets (fonts, CSS) — no external requests on load
	mux.Handle("/static/", http.StripPrefix("/static", http.FileServer(http.Dir("static"))))

	mux.HandleFunc("/files/npvt", func(w http.ResponseWriter, r *http.Request) { handleNPVTDownload(db, w, r) })

	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		channels, err := loadChannels(db)
		if err != nil {
			http.Error(w, "failed to load channels", http.StatusInternalServerError)
			log.Printf("loadChannels: %v", err)
			return
		}

		// On first load, if there is at least one channel, redirect to its messages
		// so both desktop and mobile immediately see content instead of an empty state.
		if len(channels) > 0 {
			first := channels[0]
			http.Redirect(w, r, fmt.Sprintf("/channels?id=%d&page=1", first.ID), http.StatusFound)
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

var tehranLoc = mustLoadTehranLocation()

func mustLoadTehranLocation() *time.Location {
	loc, err := time.LoadLocation("Asia/Tehran")
	if err != nil {
		// Fallback to local time if the timezone cannot be loaded.
		return time.Local
	}
	return loc
}

func formatIRTime(t time.Time) string {
	if t.IsZero() {
		return ""
	}
	// Convert to Tehran time, then to Persian (Hijri Shamsi) calendar.
	pt := ptime.New(t.In(tehranLoc))
	// Example output: 1403-01-15 13:45 (Shamsi date, 24h time)
	return pt.Format("yyyy-MM-dd HH:mm")
}

// urlRegex matches http(s), t.me, and custom schemes (nm-dns, slipnet, slipnet-enc, trojan, vless, vmess, ss, tg).
var urlRegex = regexp.MustCompile(`(https?|nm-dns|slipnet-enc|slipnet|trojan|vless|vmess|ss|tg)://[^\s<>"']+`)

// linkify escapes s for HTML and wraps URLs in clickable <a> tags. Returns safe template.HTML.
func linkify(s string) template.HTML {
	if s == "" {
		return ""
	}
	idx := urlRegex.FindAllStringIndex(s, -1)
	if len(idx) == 0 {
		return template.HTML(html.EscapeString(s))
	}
	var out []byte
	last := 0
	for _, pair := range idx {
		out = append(out, html.EscapeString(s[last:pair[0]])...)
		url := s[pair[0]:pair[1]]
		escURL := html.EscapeString(url)
		out = append(out, `<a href="`...)
		out = append(out, escURL...)
		out = append(out, `" target="_blank" rel="noopener noreferrer">`...)
		out = append(out, escURL...)
		out = append(out, `</a>`...)
		last = pair[1]
	}
	out = append(out, html.EscapeString(s[last:])...)
	return template.HTML(out)
}

func buildTemplates() (*template.Template, *template.Template, *template.Template) {
	funcMap := template.FuncMap{
		"formatIRTime": formatIRTime,
		"linkify":     linkify,
	}

	layout := template.Must(template.New("layout").Funcs(funcMap).ParseFiles(
		"templates/layout.html",
	))
	channels := template.Must(template.Must(layout.Clone()).ParseFiles(
		"templates/channels.html",
	))
	messages := template.Must(template.Must(layout.Clone()).ParseFiles(
		"templates/messages.html",
	))
	return layout, channels, messages
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
		`SELECT m.message_id, m.text, m.media_url, mf.filename, m.published_at
         FROM messages m
         LEFT JOIN message_files mf ON m.channel_id = mf.channel_id AND m.message_id = mf.message_id
         WHERE m.channel_id = ?
         ORDER BY m.published_at DESC
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
		var attachName sql.NullString
		if err := rows.Scan(&m.MessageID, &m.Text, &m.MediaURL, &attachName, &m.PublishedAt); err != nil {
			return nil, err
		}
		m.AttachmentFileName = attachName
		result = append(result, m)
	}
	return result, rows.Err()
}

func handleNPVTDownload(db *sql.DB, w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodHead {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	cStr := r.URL.Query().Get("c")
	mStr := r.URL.Query().Get("m")
	if cStr == "" || mStr == "" {
		http.Error(w, "missing c or m", http.StatusBadRequest)
		return
	}
	channelID, err := strconv.ParseInt(cStr, 10, 64)
	if err != nil {
		http.Error(w, "invalid channel id", http.StatusBadRequest)
		return
	}
	messageID, err := strconv.ParseInt(mStr, 10, 64)
	if err != nil {
		http.Error(w, "invalid message id", http.StatusBadRequest)
		return
	}

	var filename string
	var content []byte
	row := db.QueryRow(
		`SELECT filename, content FROM message_files WHERE channel_id = ? AND message_id = ?`,
		channelID, messageID,
	)
	if err := row.Scan(&filename, &content); err != nil {
		if err == sql.ErrNoRows {
			http.Error(w, "not found", http.StatusNotFound)
			return
		}
		log.Printf("handleNPVTDownload: %v", err)
		http.Error(w, "internal error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/octet-stream")
	w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=%q", filename))
	w.Header().Set("Cache-Control", "no-store")
	w.WriteHeader(http.StatusOK)
	if r.Method == http.MethodGet {
		w.Write(content)
	}
}

