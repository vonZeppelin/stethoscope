(ns stethoscope.events
  (:require [re-frame.core :as rf]
            ;; loads effect handler
            [day8.re-frame.fetch-fx]))

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
 (fn [db [_ kind {body :body}]]
   (case kind
     :load-files-list (->
                       db
                       (assoc
                        :loading-files? false
                        :next-file (:next body))
                       (update :files concat (:files body)))
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
            :url "//api.stethoscope.lbogdanov.dev/files"
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
            :url "//api.stethoscope.lbogdanov.dev/"
            :body {:url url}
            :mode :cors
            :request-content-type :json
            :response-content-types json-response-type
            :on-success [:http-success :queue-file]
            :on-failure [:http-error :queue-file]}}))

;; (rf/reg-event-fx
;;  :delete-file
;;  (fn [_ [_ file-id]]
;;    {:http-xhrio {:method :delete
;;                  :uri "/api/files/{file}"
;;                  :params {:file file}
;;                  :format (ajax/json-request-format)
;;                  :response-format (ajax/json-response-format {:keywords? true})
;;                  :on-success [:http-success :delete-file]
;;                  :on-failure [:http-error :delete-file]}}))
