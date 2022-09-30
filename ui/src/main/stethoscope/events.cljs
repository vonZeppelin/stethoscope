(ns stethoscope.events
  (:require [lambdaisland.uri :refer [join uri]]
            [re-frame.core :as rf]
            ;; loads effect handler
            [day8.re-frame.fetch-fx]))

(defonce ^:private api-host
  (uri "//api.stethoscope.lbogdanov.dev/"))

(defonce ^:private json-response-type
  {#"application/.*json" :json})

(rf/reg-event-db
 :init
 (fn [_ _]
   {:files []
    :next-file ""
    :loading-files? false}))

(rf/reg-event-db
 :http-success
 (fn [db [_ kind & rest]]
   (case kind
     :load-files-list (let [[{body :body}] rest]
                        (-> db
                            (assoc :loading-files? false
                                   :next-file (:next body))
                            (update :files concat (:files body))))
     :queue-file (let [[{body :body}] rest]
                   (update db :files into [body]))
     :delete-file (let [[deleted-file-id] rest
                        deleted-file? (fn [{file-id :id}]
                                        (= deleted-file-id file-id))]
                    (update db :files (partial remove deleted-file?)))
     db)))

(rf/reg-event-db
 :http-error
 (fn [db [_ kind]]
   (case kind
     :load-files-list (assoc db :loading-files? false)
     db)))

(rf/reg-event-fx
 :load-files-list
 (fn [{db :db}]
   {:fetch {:method :get
            :url (join api-host "files")
            :params {:next (:next-file db)}
            :mode :cors
            :response-content-types json-response-type
            :on-success [:http-success :load-files-list]
            :on-failure [:http-error :load-files-list]}
    :db (assoc db :loading-files? true)}))

(rf/reg-event-fx
 :queue-file
 (fn [_ [_ url]]
   {:fetch {:method :post
            :url (join api-host "files")
            :body {:url url}
            :mode :cors
            :request-content-type :json
            :response-content-types json-response-type
            :on-success [:http-success :queue-file]
            :on-failure [:http-error :queue-file]}}))

(rf/reg-event-fx
 :delete-file
 (fn [_ [_ file-id]]
   {:fetch {:method :delete
            :url (join api-host "files/" file-id)
            :mode :cors
            :request-content-type :json
            :response-content-types json-response-type
            :on-success [:http-success :delete-file file-id]
            :on-failure [:http-error :delete-file]}}))
