(ns stethoscope.views
  (:require ["antd" :as antd]
            ["@ant-design/icons" :as icons]
            [reagent.core :as r]
            [reagent.dom :as rdom]
            [re-frame.core :as rf]))

(defn list-files-comp []
  (letfn [(file-renderer [{:keys [title description thumbnail]}]
            (let [avatar (r/create-element
                          antd/Avatar
                          #js{:src thumbnail
                              :shape "square"
                              :size 150})
                  delete-button (r/create-element
                                 antd/Button
                                 #js{:icon (r/create-element icons/DeleteOutlined)
                                     :onClick print})
                  play-button (r/create-element
                               antd/Button
                               #js{:icon (r/create-element icons/PlayCircleOutlined)
                                   :onClick print})]
              (r/as-element
               [:> antd/List.Item {:actions (array play-button delete-button)}
                [:> antd/List.Item.Meta {:title title
                                         :description description
                                         :avatar avatar}]])))
          (file-id [file]
            (:id file))]
    [:> antd/List {:dataSource (to-array @(rf/subscribe [:files]))
                   :loading @(rf/subscribe [:loading-files?])
                   :renderItem file-renderer
                   :rowKey file-id}]))

(defn queue-file-comp []
  (let [[form] (antd/Form.useForm)]
    [:> antd/Form {:form form
                   :name "queue-file"
                   :onFinish (fn [fields]
                               (form.resetFields)
                               (rf/dispatch [:queue-file fields.link]))}
     [:> antd/Form.Item {:label "YouTube link"
                         :name "link"
                         :rules (clj->js [{:required true}
                                          {:type "url"}])}
      [:> antd/Input {:allowClear true}]]
     [:> antd/Form.Item
      [:> antd/Button {:htmlType "submit"
                       :icon (r/create-element icons/DownloadOutlined)
                       :type "primary"}
       "Download"]]]))

(defn ui []
  [:<>
   [:f> queue-file-comp]
   [list-files-comp]])

(defn render []
  (rdom/render
   [ui]
   (js/document.getElementById "app")))
