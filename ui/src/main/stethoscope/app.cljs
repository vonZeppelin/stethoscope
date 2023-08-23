(ns stethoscope.app
  (:require [cljs.core.async :refer [<! go go-loop timeout]]
            [cljs.core.async.interop :refer [<p!]]
            [lambdaisland.fetch :as fetch]
            [lambdaisland.uri :refer [join uri]]
            [reagent.core :as r]))

(defonce state (r/atom {:files {}
                        :loading-files false}))

(defonce api-host
  (uri "//api-stethoscope.lbogdanov.dev/"))

(defn- poll-file [file-id]
  (go-loop []
    (let [{body :body
           status :status} (<p! (fetch/get (join api-host "files")
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

(defn queue-file [url error-fn]
  (go
    (try
      (let [{body :body
             status :status} (<p! (fetch/post (join api-host "files")
                                              {:accept :json
                                               :content-type :json
                                               :credentials :include
                                               :body {:url url}}))]
        (cond
          (<= 200 status 299) (let [file (js->clj body :keywordize-keys true)
                                    {file-id :id} file]
                                (swap! state update :files into [[file-id file]])
                                (<! (poll-file file-id)))
          (<= 400 status 499) (error-fn body)
          :else (error-fn "Error queueing file")))
      (catch :default e
        (error-fn (.. e -cause -message))))))

(defn delete-file [file-id error-fn]
  (go
    (try
      (let [{body :body
             status :status} (<p! (fetch/delete (join api-host "files/" file-id)
                                                {:accept :json
                                                 :credentials :include}))]
        (if (<= 200 status 299)
          (let [{file-id :id}  (js->clj body :keywordize-keys true)]
            (swap! state update :files dissoc file-id))
          (error-fn "Error deleting file")))
      (catch :default e
        (error-fn (.. e -cause -message))))))

(defn load-files [error-fn]
  (go
    (try
      (swap! state assoc :loading-files true)
      (let [{body :body
             status :status} (<p! (fetch/get (join api-host "files")
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
