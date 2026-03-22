## 1 概览

介绍 雅致靓的erp项目`addon`开发流程及一些基础规范

### 1.1 目录结构

```tree
.
└── yzl_addons
    ├── account_extension
    ├── account_report
    ├── api-service-management
    ├── auth_oauth_wechat
    ├── authority_management
    ├── biometric_identification
    ├── data_import_management
    ......

```
新创建的模块再`yzl_addons`目录下

### 1.2 命名规则

最多不超过4个单词组合

一般名称： [odoo模块名称]_[服务类型]_[服务名称]

#### 1.2.1 odoo模块名称

如果是 `odoo`已有的模块 例如 `account`、`auth`,`sale`等，请使用历史的模块，新模块与项目经理沟通后决定。

#### 1.2.2 服务类型

例如已有的 `extension`,`report`,`request`等

#### 1.2.3 自己的服务名称

例如 `service-management`, `wechat`等

## 2 开始

初始项目使用命令快速初始化

```
./odoo-bin scaffold quickstart_doc  ./oscg/yzl_addons
```

### 2.1 目录结构

```text
yzl_addons/quickstart_doc
├── __init__.py
├── __manifest__.py
├── controllers
│   ├── __init__.py
│   └── controllers.py
├── demo
│   └── demo.xml
├── models
│   ├── __init__.py
│   └── models.py
├── security
│   └── ir.model.access.csv
└── views
    ├── templates.xml
    └── views.xml

```
### 2.2 修改 __manifest__.py

```py
# -*- coding: utf-8 -*-  
{  
    'name': "雅致靓插件快速入门文档",  
    'summary': "雅致靓插件快速入门文档",  
    'description': """  
        雅致靓插件快速入门文档  
    """,  
    'author': "YZL",  
    'website': "https://www.yzl.co.zw/",  
    'category': 'YZL/YZL',  
    'license': 'LGPL-3',  
    'version': '0.1',  
    # any module necessary for this one to work correctly  
    'depends': ['yzl_base'],  
    'installable': True,  
    'application': True,  
    'auto_install': False,  
}
```