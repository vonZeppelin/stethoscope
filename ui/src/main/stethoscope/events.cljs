(ns stethoscope.events
  (:require [ajax.core :as ajax]
            [re-frame.core :as rf]
            ;; loads effect handler
            [day8.re-frame.http-fx]))

(rf/reg-event-db
 :init
 (fn [_ _]
   {:files []
    :next-file ""
    :loading-files? false}))

(rf/reg-event-db
 :http-success
 (fn [db [_ kind resp]]
   (case kind
     :load-files-list (->
                       db
                       (assoc
                        :loading-files? false
                        :next-file (:next-file resp))
                       (update :files concat (:files resp)))
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
   {:http-xhrio {:method :get
                 :uri "/files"
                 :params {:next (:next-file db)}
                 :response-format (ajax/json-response-format {:keywords? true})
                 :on-success [:http-success :load-files-list]
                 :on-failure [:http-error :load-files-list]}
    :db (assoc db :loading-files? true)}))

(rf/reg-event-fx
 :queue-file
 (fn [_ [_ url]]
   {:http-xhrio {:method :post
                 :uri "/files"
                 :params {:url url}
                 :format (ajax/json-request-format)
                 :response-format (ajax/json-response-format {:keywords? true})
                 :on-success [:http-success :queue-file]
                 :on-failure [:http-error :queue-file]}}))

;; (rf/reg-event-fx
;;  :delete-file
;;  (fn [_ [_ file-id]]
;;    {:http-xhrio {:method :delete
;;                  :uri "/files/{file}"
;;                  :params {:file file}
;;                  :format (ajax/json-request-format)
;;                  :response-format (ajax/json-response-format {:keywords? true})
;;                  :on-success [:http-success :delete-file]
;;                  :on-failure [:http-error :delete-file]}}))
