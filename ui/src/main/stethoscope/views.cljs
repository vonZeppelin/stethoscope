(ns stethoscope.views
  (:require ["antd" :as antd]
            ["@ant-design/icons" :as icons]
            [reagent.core :as r]
            [reagent.dom :as rdom]
            [re-frame.core :as rf]))

(defn list-files-comp []
  (letfn [(file-renderer [{:keys [id title description thumbnail]}]
            (let [avatar-image (r/create-element
                                antd/Image
                                #js{:src thumbnail})
                  avatar (r/create-element
                          antd/Avatar
                          #js{:src avatar-image
                              :shape "square"
                              :size 150})
                  delete-button (r/create-element
                                 antd/Button
                                 #js{:icon (r/create-element icons/DeleteOutlined)
                                     :size "large"})
                  confirm-delete (r/create-element
                                  antd/Popconfirm
                                  #js{:title "Delete this video?"
                                      :placement "left"
                                      :onConfirm (fn [_]
                                                   (rf/dispatch [:delete-file id]))}
                                  delete-button)]
              (r/as-element
               [:> antd/List.Item {:actions (array confirm-delete)}
                [:> antd/List.Item.Meta {:title title
                                         :description (r/create-element
                                                       antd/Typography.Paragraph
                                                       (clj->js {:ellipsis {:expandable true
                                                                            :rows 3
                                                                            :symbol "more"}
                                                                 :style {:whiteSpace "pre-wrap"}})
                                                       description)
                                         :avatar avatar}]])))]
    [:> antd/List {:bordered true
                   :dataSource (to-array @(rf/subscribe [:files]))
                   :loading @(rf/subscribe [:loading-files?])
                   :renderItem file-renderer
                   :rowKey :id}]))

(defn queue-file-comp []
  (let [[form] (antd/Form.useForm)]
    [:> antd/Form {:form form
                   :name "queue-file"
                   :layout "inline"
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
  [:> antd/Layout
   [:> antd/Layout.Header]
   [:> antd/Layout.Content
    [:> antd/Row
     [:> antd/Col {:offset 5 :span 14}
      [:f> queue-file-comp]]]
    [:> antd/Row
     [:> antd/Col {:offset 5 :span 14}
      [list-files-comp]]]]
   [:> antd/Layout.Footer {:style {:textAlign "center"}}
    "2022 Stethoscope"]])

(defn render []
  (rdom/render
   [ui]
   (js/document.getElementById "app")))
