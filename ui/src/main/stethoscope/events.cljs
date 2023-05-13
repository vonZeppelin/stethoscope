(ns stethoscope.events
  (:require [lambdaisland.uri :refer [join uri]]
            [re-frame.core :as rf]
            ;; load effect handlers
            [day8.re-frame.fetch-fx]
            [stethoscope.effects]))

(defonce ^:private api-host
  (uri "//api-stethoscope.lbogdanov.dev/"))

(defonce ^:private json-response-type
  {#"application/.*json" :json})

(rf/reg-event-db
 :init
 (fn [_ _]
   {:files {}
    :queue #{}
    :next-file ""
    :loading-files? false}))

(rf/reg-event-db
 :http-error
 (fn [db [_ kind]]
   (case kind
     :files-loaded (assoc db :loading-files? false)
     db)))

(rf/reg-event-fx
 :http-success
 (fn [{db :db} [_ kind & rest]]
   (case kind
     :files-loaded (let [[{body :body}] rest
                         files (:files body)
                         next-file (:next body)]
                     {:db (-> db
                              (assoc :loading-files? false
                                     :next-file next-file)
                              (update :files merge (zipmap
                                                    (map :id files)
                                                    files)))})
     :file-queued (let [[{file :body}] rest
                        file-id (:id file)]
                    {:db (-> db
                             (update :files (partial merge {file-id file}))
                             (update :queue conj file-id))
                     :timeout {:event :poll-queue}})
     :queue-polled (let [[{body :body}] rest
                         files (:files body)
                         update-db (fn [db {file-id :id :as file}]
                                     (-> db
                                         (update :files assoc file-id file)
                                         (update :queue disj file-id)))
                         db (reduce update-db db files)]
                     (if (empty? (:queue db))
                       {:db db}
                       {:db db :timeout {:event :poll-queue :timeout 2.5}}))
     :file-deleted (let [[{file :body}] rest
                         file-id (:id file)]
                     {:db (update db :files dissoc file-id)})
     {:db db})))

(rf/reg-event-fx
 :load-files
 (fn [{db :db}]
   {:db (assoc db :loading-files? true)
    :fetch {:method :get
            :url (join api-host "files")
            :params {:next (:next-file db)}
            :mode :cors
            :response-content-types json-response-type
            :on-success [:http-success :files-loaded]
            :on-failure [:http-error :files-loaded]}}))

(rf/reg-event-fx
 :queue-file
 (fn [_ [_ url]]
   {:fetch {:method :post
            :url (join api-host "files")
            :body {:url url}
            :mode :cors
            :request-content-type :json
            :response-content-types json-response-type
            :on-success [:http-success :file-queued]
            :on-failure [:http-error :file-queued]}}))

(rf/reg-event-fx
 :poll-queue
 (fn [{db :db}]
   {:fetch {:method :get
            :url (join api-host "files")
            :params {:id (to-array (:queue db))}
            :mode :cors
            :request-content-type :json
            :response-content-types json-response-type
            :on-success [:http-success :queue-polled]
            :on-failure [:http-error :queue-polled]}}))

(rf/reg-event-fx
 :delete-file
 (fn [_ [_ file-id]]
   {:fetch {:method :delete
            :url (join api-host "files/" file-id)
            :mode :cors
            :request-content-type :json
            :response-content-types json-response-type
            :on-success [:http-success :file-deleted]
            :on-failure [:http-error :file-deleted]}}))
