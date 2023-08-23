(ns stethoscope.ui
  (:require [cljs.core.async :refer [<! go]]
            ["antd" :as antd]
            ["@ant-design/icons" :as icons]
            ["dayjs" :as dayjs]
            ["dayjs/plugin/duration" :as duration]
            [lambdaisland.uri :refer [join uri uri-str]]
            [reagent.core :as r]
            [reagent.dom :as rdom]
            [stethoscope.app :as app]))

(dayjs/extend duration)

(defn- file-renderer [message confirm {:keys [id title description thumbnail duration]}]
  (let [avatar-width 150
        confirm-delete (fn [_]
                         (confirm (clj->js {:title "Delete this file?"
                                            :content title
                                            :okText "Yes"
                                            :cancelText "No"
                                            :okButtonProps {:danger true
                                                            :type "primary"}
                                            :onOk (fn [close]
                                                    (go
                                                      (<! (app/delete-file id message.error))
                                                      (close)))})))
        avatar (r/as-element
                [:<>
                 [:div.file-duration
                  [:> icons/ClockCircleOutlined]
                  (-> dayjs
                      (.duration duration "s")
                      (.format "HH:mm:ss"))]
                 [:> antd/Image {:preview {:toolbarRender (constantly nil)}
                                 :src thumbnail
                                 :width avatar-width}]
                 [:div.file-controls
                  [:> antd/Button {:icon (r/create-element icons/YoutubeOutlined)
                                   :type "text"
                                   :href (-> (uri "https://youtu.be/")
                                             (join id)
                                             uri-str)
                                   :target "_blank"}]
                  [:> antd/Button {:icon (r/create-element icons/DownloadOutlined)
                                   :type "text"
                                   :href (-> (uri app/api-host)
                                             (join "feed/" id)
                                             uri-str)
                                   :target "_blank"}]
                  [:> antd/Button {:icon (r/create-element icons/DeleteOutlined)
                                   :type "text"
                                   :on-click confirm-delete}]]])]
    (r/as-element
     [:> antd/List.Item
      ;; fully downloaded item has a non-blank title
      (if title
        [:> antd/List.Item.Meta {:avatar avatar
                                 :title title
                                 :description (r/as-element
                                               [:> antd/Typography.Paragraph {:class-name "file-description"
                                                                              :ellipsis {:expandable true
                                                                                         :rows 2
                                                                                         :symbol "more"}}
                                                description])}]
        [:> antd/Skeleton {:active true
                           :avatar {:shape "square"
                                    :size avatar-width}}])])))

(defn list-files-comp []
  (r/with-let [app (antd/App.useApp)
               message (.-message app)
               confirm (.. app -modal -confirm)
               _ (app/load-files message.error)]
    [:> antd/List {:class-name "files-list"
                   :bordered true
                   :dataSource (-> @app/state
                                   :files
                                   vals
                                   to-array)
                   :loading (:loading-files @app/state)
                   :render-item #(file-renderer message confirm %)
                   :row-key :id}]))

(defn add-file-comp []
  (r/with-let [[form] (antd/Form.useForm)
               message (.-message (antd/App.useApp))]
    [:> antd/Form {:form form
                   :name "add-files"
                   :auto-complete "off"
                   :layout "inline"
                   :on-finish (fn [fields]
                                (form.resetFields)
                                (app/queue-file fields.link message.error))}
     [:> antd/Form.Item {:label "YouTube link"
                         :name "link"
                         :rules [{:required true}
                                 {:type "url"}]}
      [:> antd/Input {:allow-clear true}]]
     [:> antd/Form.Item
      [:> antd/Button {:html-type "submit"
                       :icon (r/create-element icons/DownloadOutlined)
                       :type "primary"}
       "Download"]]]))

(defn ui []
  [:> antd/ConfigProvider {:theme {:algorithm antd/theme.darkAlgorithm}}
   [:> antd/App
    [:> antd/Layout
     [:> antd/Layout.Header
      "Stethoscope"]
     [:> antd/Layout.Content
      [:f> add-file-comp]
      [:f> list-files-comp]]
     [:> antd/Layout.Footer
      "2023 Stethoscope"]]]])

(defn render []
  (rdom/render
   [ui]
   (js/document.getElementById "app")))

(defn ^:dev/after-load main []
  (render))
