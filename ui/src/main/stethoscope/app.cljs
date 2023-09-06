(ns stethoscope.app
  (:require [cljs.core.async :refer [<! go go-loop timeout]]
            [cljs.core.async.interop :refer [<p!]]
            [lambdaisland.fetch :as fetch]
            [lambdaisland.uri :refer [join uri]]
            [reagent.core :as r]))

(defonce state (r/atom {:mode "youtube"
                        :files {}
                        :loading-files false
                        :book-upload nil}))

(defonce api-host
  (uri "https://api-stethoscope.lbogdanov.dev/"))

(defn- poll-file [file-id]
  (go-loop []
    (let [{body :body
           status :status} (<p! (fetch/get
                                 (join api-host "files")
                                 {:accept :json
                                  :credentials :include
                                  :query-params {"id" file-id}}))]
      (if (<= 200 status 299)
        (let [{files :files} (js->clj body :keywordize-keys true)]
          (if (empty? files)
            (do
              (<! (timeout 2500))
              (recur))
            (swap! state update :files merge (zipmap (map :id files) files))))
        (throw
         (ex-info "Error polling file" {}))))))

(defn add-youtube [url error-fn]
  (go
    (try
      (let [{body :body
             status :status} (<p! (fetch/post
                                   (join api-host "files/youtube/add")
                                   {:accept :json
                                    :content-type :json
                                    :credentials :include
                                    :body {:url url}}))]
        (cond
          (<= 200 status 299) (let [file (js->clj body :keywordize-keys true)
                                    {youtube-id :id} file]
                                (swap! state update :files assoc youtube-id file)
                                (<! (poll-file youtube-id)))
          (<= 400 status 499) (error-fn body)
          :else (error-fn "Error queueing file")))
      (catch :default e
        (error-fn (.. e -cause -message))))))

(defn delete-file [file-id error-fn]
  (go
    (try
      (let [{body :body
             status :status} (<p! (fetch/delete
                                   (join api-host "files/" file-id)
                                   {:accept :json
                                    :credentials :include}))]
        (if (<= 200 status 299)
          (let [{file-id :id} (js->clj body :keywordize-keys true)]
            (swap! state update :files dissoc file-id))
          (error-fn "Error deleting file")))
      (catch :default e
        (error-fn (.. e -cause -message))))))

(defn load-files [error-fn]
  (go
    (try
      (swap! state assoc :loading-files true)
      (let [{body :body
             status :status} (<p! (fetch/get
                                   (join api-host "files")
                                   {:accept :json
                                    :credentials :include}))]
        (if (<= 200 status 299)
          (let [{files :files} (js->clj body :keywordize-keys true)
                files-by-id (zipmap (map :id files) files)]
            (swap! state update :files merge files-by-id))
          (error-fn "Error loading files")))
      (catch :default e
        (error-fn (.. e -cause -message)))
      (finally
        (swap! state assoc :loading-files false)))))

(defn start-book-upload [error-fn]
  (go
    (try
      (let [{body :body
             status :status} (<p! (fetch/post
                                   (join api-host "files/book/add")
                                   {:accept :json
                                    :credentials :include}))]
        (cond
          (<= 200 status 299) (let [{book-id :id} (js->clj body :keywordize-keys true)]
                                (swap! state assoc :book-upload book-id))
          :else (error-fn "Error starting book upload")))
      (catch :default e
        (error-fn (.. e -cause -message))))))

(defn upload-book-chapter [book-id chapter error-fn]
  (go
    (try
      (let [{body :body
             status :status} (<p! (fetch/post
                                   (join api-host "files/book/" (str book-id "/") "add_chapter")
                                   {:accept :json
                                    :content-type :json
                                    :credentials :include
                                    :body {:filename chapter}}))]
        (cond
          (<= 200 status 299) (let [{upload-url :url} (js->clj body :keywordize-keys true)]
                                upload-url)
          :else (error-fn (str "Error uploading book chapter '" chapter "'"))))
      (catch :default e
        (error-fn (.. e -cause -message))))))

(defn complete-book-upload [book-id error-fn]
  (go
    (try
      (let [{body :body
             status :status} (<p! (fetch/post
                                   (join api-host "files/book/" (str book-id "/") "complete")
                                   {:accept :json
                                    :credentials :include}))]
        (cond
          (<= 200 status 299) (let [book (js->clj body :keywordize-keys true)
                                    {book-id :id} book]
                                (swap! state update :files assoc book-id book)
                                (<! (poll-file book-id)))
          (<= 400 status 499) (error-fn body)
          :else (error-fn "Error completing book upload")))
      (catch :default e
        (error-fn (.. e -cause -message)))
      (finally
        (swap! state dissoc :book-upload)))))
