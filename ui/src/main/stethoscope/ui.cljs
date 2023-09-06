(ns stethoscope.ui
  (:require [cljs.core.async :refer [<! go]]
            ["antd" :as antd]
            ["@ant-design/icons" :as icons]
            ["copy-to-clipboard" :as copy]
            ["dayjs" :as dayjs]
            ["dayjs/plugin/duration" :as duration]
            [lambdaisland.uri :refer [join uri uri-str]]
            [reagent.core :as r]
            [reagent.dom :as rdom]
            [stethoscope.app :as app]))

(dayjs/extend duration)

(defn- file-renderer [message confirm {:keys [id title description type thumbnail duration]}]
  (let [avatar-width 150
        confirm-delete (fn [_]
                         (confirm (clj->js {:title "Delete this item?"
                                            :content title
                                            :centered true
                                            :okText "Yes"
                                            :cancelText "No"
                                            :okButtonProps {:danger true
                                                            :type "primary"}
                                            :onOk (fn [close]
                                                    (go
                                                      (<! (app/delete-file id (.-error message)))
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
                  (if (= type "youtube")
                    [:<>
                     [:> antd/Button {:icon (r/create-element icons/ExportOutlined)
                                      :title "Go to Youtube"
                                      :type "text"
                                      :href (-> (uri "https://youtu.be/")
                                                (join id)
                                                uri-str)
                                      :target "_blank"}]
                     [:> antd/Button {:icon (r/create-element icons/DownloadOutlined)
                                      :type "text"
                                      :title "Download audio"
                                      :href (-> (uri app/api-host)
                                                (join "media/" id)
                                                uri-str)
                                      :target "_blank"}]]
                    [:> antd/Tooltip {:title "Copied!"
                                      :trigger "click"}
                     [:> antd/Button {:icon (r/create-element icons/LinkOutlined)
                                      :title "Copy link to clipboard"
                                      :type "text"
                                      :on-click #(copy
                                                  (-> (uri app/api-host)
                                                      (join "book/" (str id "/") "feed")
                                                      uri-str)
                                                  #js{:format "text/plain"})}]])
                  [:> antd/Button {:icon (r/create-element icons/DeleteOutlined)
                                   :title "Delete item"
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

(defn- custom-request [req]
  (let [action (.-action req)
        file (.-file req)
        on-success (.-onSuccess req)
        on-error (.-onError req)
        on-progress (.-onProgress req)
        xhr (js/XMLHttpRequest.)]
    (doto (.-upload xhr)
      (.addEventListener
       "load"
       #(on-success (.-response xhr)))
      (.addEventListener
       "error"
       #(on-error (js/Error. (.-statusText xhr))
                  (.-response xhr)))
      (.addEventListener
       "progress"
       #(when (.-lengthComputable %)
          (let [loaded (float (.-loaded %))
                total (float (.-total %))
                percent (* (/ loaded total) 100)]
            (on-progress #js{:percent percent})))))
    (doto xhr
      (.open "PUT" action)
      (.send file))))

(defn list-files-comp []
  (r/with-let [app (.useApp antd/App)
               message (.-message app)
               confirm (.. app -modal -confirm)
               _ (app/load-files (.-error message))]
    (let [{:keys [files loading-files mode]} @app/state]
      [:> antd/List {:class-name "files-list"
                     :bordered true
                     :dataSource (->> (vals files)
                                      (filter #(= (:type %) mode))
                                      to-array)
                     :loading loading-files
                     :render-item #(file-renderer message confirm %)
                     :row-key :id}])))

(defn add-youtube-comp []
  (r/with-let [message (.-message (.useApp antd/App))]
    (let [[form] (.useForm antd/Form)]
      [:> antd/Form {:form form
                     :name "add-youtube"
                     :auto-complete "off"
                     :layout "inline"
                     :on-finish (fn [fields]
                                  (.resetFields form)
                                  (app/add-youtube (.-link fields)
                                                   (.-error message)))}
       [:> antd/Form.Item {:label "YouTube link"
                           :name "link"
                           :rules [{:required true}
                                   {:type "url"}]}
        [:> antd/Input {:allow-clear true}]]
       [:> antd/Form.Item
        [:> antd/Button {:html-type "submit"
                         :icon (r/create-element icons/DownloadOutlined)
                         :type "primary"}
         "Download"]]])))

(defn add-audiobook-comp []
  (r/with-let [message (.-message (.useApp antd/App))]
    (let [book-id (:book-upload @app/state)]
      [:div
       (when book-id
         [:> antd/Upload.Dragger {:accept ".mp3"
                                  :multiple true
                                  :show-upload-list #js{:showPreviewIcon false
                                                        :showDownloadIcon false
                                                        :showRemoveIcon false}
                                  :customRequest custom-request
                                  :action #(js/Promise.
                                            (fn [resolve reject]
                                              (go
                                                (if-let [url (<! (app/upload-book-chapter
                                                                  book-id
                                                                  (.-name %)
                                                                  (.-error message)))]
                                                  (resolve url)
                                                  (reject nil)))))}
          [:p.ant-upload-drag-icon
           [:> icons/InboxOutlined]]
          [:p.ant-upload-text
           "Click or drag files here to upload"]])
       [:> antd/Button {:icon (r/create-element icons/CheckCircleOutlined)
                        :type "primary"
                        :on-click #(if book-id
                                     (app/complete-book-upload book-id (.-error message))
                                     (app/start-book-upload (.-error message)))}
        (if book-id "Complete upload" "Upload book")]])))

(defn ui []
  (r/with-let [mode (r/cursor app/state [:mode])]
    [:> antd/ConfigProvider {:theme {:algorithm (.-darkAlgorithm antd/theme)}}
     [:> antd/App
      [:> antd/Layout
       [:> antd/Layout.Header
        [:span "Stethoscope"]
        [:> antd/Segmented {:class-name "mode-selector"
                            :options [{:label "Youtube videos"
                                       :value "youtube"
                                       :icon (r/create-element icons/YoutubeOutlined)}
                                      {:label "Audibooks"
                                       :value "audiobook"
                                       :icon (r/create-element icons/BookOutlined)}]
                            :value @mode
                            :on-change #(reset! mode %)}]]
       [:> antd/Layout.Content
        (if (= "youtube" @mode)
          [:f> add-youtube-comp]
          [:f> add-audiobook-comp])
        [:f> list-files-comp]]
       [:> antd/Layout.Footer
        "2023 Stethoscope"]]]]))

(defn render []
  (rdom/render
   [ui]
   (.getElementById js/document "app")))

(defn ^:dev/after-load main []
  (render))
