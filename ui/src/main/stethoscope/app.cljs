(ns stethoscope.app
  (:require [ajax.core :as ajax]
            ["antd" :as antd]
            [reagent.core :as r]
            [reagent.dom :as rdom]
            [re-frame.core :as rf]
            ;; loads effect handler
            [day8.re-frame.http-fx]))

(rf/reg-event-db
 :init
 (fn [_ _]
   {:files []
    :loading-files? false}))

(rf/reg-event-db
  :http-success
  (fn [db [_ kind resp]]
    (condp = kind
      :load-files-list (assoc
                        db
                        :files resp
                        :loading-files? false)
      :queue-file db)))

(rf/reg-event-db
 :http-error
 (fn [db [_ kind]]
   (condp = kind
     :load-files-list (assoc db :loading-files? false)
     :queue-file db)))

(rf/reg-event-fx
 :load-files-list
 (fn [{db :db} _]
   {:http-xhrio {:method :get
                 :uri "/files"
                 :response-format (ajax/json-response-format)
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
                 :response-format (ajax/json-response-format)
                 :on-success [:http-success :queue-file]
                 :on-failure [:http-error :queue-file]}}))

(rf/reg-sub
 :files
 (fn [db _]
   (:files db)))

(rf/reg-sub
 :loading-files?
 (fn [db _]
   (:loading-files? db)))

;; ui

(defn list-files-comp []
  (letfn [(file-renderer [file]
            (r/as-element
             [:> antd/List.Item {:key file.id}
              [:> antd/List.Item.Meta {:description file.description
                                       :title file.name}]]))]
    [:> antd/List {:dataSource @(rf/subscribe [:files])
                   :loading @(rf/subscribe [:loading-files?])
                   :renderItem file-renderer}]))

(defn queue-file-comp []
  [:> antd/Form {:name "queue-file"
                 :onFinish #(rf/dispatch [:queue-file (.-link %)])}
   [:> antd/Form.Item {:label "YouTube link"
                       :name "link"
                       :rules (clj->js [{:required true}
                                        {:type "url"}])}
    [:> antd/Input {:allowClear true}]]
   [:> antd/Form.Item
    [:> antd/Button {:htmlType "submit"
                     :type "primary"}
     "Download"]]])

(defn ui []
  [:<>
   [queue-file-comp]
   [list-files-comp]])

;; app init

(defn render []
  (rdom/render
   [ui]
   (js/document.getElementById "app")))

(defn ^:dev/after-load clear-cache-and-render! []
  (rf/clear-subscription-cache!)
  (render))

(defn main []
  (rf/dispatch-sync [:init])
  (rf/dispatch [:load-files-list])
  (render))
